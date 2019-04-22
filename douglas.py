import collections
import datetime
from email.utils import parsedate_to_datetime
import json
import logging
import os
import urllib
import re

from jinja2 import Environment, FileSystemLoader
from nested_lookup import nested_lookup
from PIL import Image, ImageFile
import requests
import requests_cache
from slugify import slugify
import xmltodict


from config import CONFIG


logFormatter = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(format=logFormatter, level=logging.DEBUG)
logger = logging.getLogger(__name__)

requests_cache.install_cache('demo_cache')

file_loader = FileSystemLoader('templates')
env = Environment(loader=file_loader)


deadline = datetime.datetime.now() - datetime.timedelta(days=90)
deadline = int(deadline.timestamp())

# Logs


def add_to_fails(url, message):
    print(message)
    with open("fail_log.txt", "a") as f:
        f.write(url + ":" + message + "\n")


# Process Feeds
def get_feed_urls():
    urls = []
    for location in CONFIG['LOCATIONS']:
        file_path = os.path.join(os.getcwd(), 'data', location)
        print(file_path)
        with open(file_path) as f:
            temp_urls = f.read().splitlines()
            urls.extend(temp_urls)
    urls = list(set(urls))
    return urls



def get_podcasts():
    podcasts = []
    urls = get_feed_urls()
    count = 0
    for url in urls:
        podcast = parse_podcast(url)
        if podcast is None:
            continue
        podcast['index_id'] = count
        count = count + 1
        podcasts.append(podcast)
    return podcasts


# Process Feed

def old_parse_podcast(url):
    logger.debug('parsing: ' + url)
    clean_dict = {}
    try:
        response = requests.get(url)
    except requests.exceptions.MissingSchema:
        add_to_fails(url, " Bad URL")
        return None

    if response.status_code is not 200:
        add_to_fails(url, "Returned " + str(response.status_code))
        return None

    try:
        messy_dict = xmltodict.parse(response.content)
    except:
        add_to_fails(url, "Could Not Parse")
        return None
    #messy_dict['rss']['channel']['item'] = []

    #print(json.dumps(messy_dict, indent=4))
    try:
        items = messy_dict['rss']['channel']['item']
    except KeyError:
        add_to_fails(url, "No Items")
        return None

    clean_dict['lastPublished'] = None
    has_enclosure = False
    for item in items:
        if 'enclosure' in item:
            has_enclosure = True
            publishedDate = parsedate_to_datetime(item['pubDate'])
            publishedDate = int(publishedDate.timestamp())
            if clean_dict['lastPublished'] is None:
                clean_dict['lastPublished'] = publishedDate
            elif publishedDate > clean_dict['lastPublished']:
                clean_dict['lastPublished'] = publishedDate
    if not has_enclosure:
        add_to_fails(url, "No Enclosures")
        return None
    if clean_dict['lastPublished'] > deadline:
        clean_dict['active'] = True
    else:
        clean_dict['active'] = False
    
    if not clean_dict['active']:
        return None

    clean_dict['categories'] = []
    try:
        categories = nested_lookup('@text', messy_dict['rss']['channel']['itunes:category'])
    except KeyError:
        categories = []
    for category in categories:
        fixed_category = category.replace("&", "and")
        clean_dict['categories'].append(fixed_category)

    try:
        clean_dict['description'] = messy_dict['rss']['channel']['itunes:summary']
    except KeyError:
        clean_dict['description'] = messy_dict['rss']['channel']['description']
    clean_dict['image'] = messy_dict['rss']['channel']['itunes:image']['@href']
    try:
        clean_dict['link'] = messy_dict['rss']['channel']['link']
    except KeyError:
        logger.debug("    Feed Has No Link")
        add_to_fails(url, "Feed Has No Link")
        return None
        

    clean_dict['title'] = messy_dict['rss']['channel']['title']
    clean_dict['slug'] = slugify(clean_dict['title'])
    
    return clean_dict


# Podcaster Podcast

def get_recent_podcasters_podcast_episodes():
    episodes = []
    feed_url = "https://seattlepodcasterspodcast.libsyn.com/rss"
    response = requests.get(feed_url)
    pod_dict = xmltodict.parse(response.content)
    for item in pod_dict['rss']['channel']['item']:
        episode = {}
        episode['title'] = item['title']
        episode['link'] = item['link']
        episodes.append(episode)
    return episodes
    


# Process Cover Art
def generate_all_cover_art(podcasts):
    for podcast in podcasts:
        if podcast['active']:
            generate_cover_art(podcast)

def generate_cover_art(podcast):
    file_path = os.path.join(CONFIG['OUTPUT_DIR'] , "cover_art", podcast['slug'] + ".jpg")
    print(podcast['image'])
    size = CONFIG['COVER_ART_SIZE'], CONFIG['COVER_ART_SIZE']
    if os.path.isfile(file_path):
        print("   already have image")
        return
    req = urllib.request.Request(
        podcast['image'], 
        data=None, 
        headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
        }
    )
    try: 
        f = urllib.request.urlopen(req)
    except:
        return
    image = Image.open(f)
    image = image.convert('RGB')
    image.thumbnail(size)
    image.save(file_path, "JPEG", optimize=True)



# Render Pages

def render_index(number_of_podcasts):
    podcasters_podcast_episodes = get_recent_podcasters_podcast_episodes()
    file_path = os.path.join(CONFIG['OUTPUT_DIR'] , "index.html")
    template = env.get_template('index.html')
    output = template.render(number_of_podcasts=number_of_podcasts, podcasters_podcast_episodes=podcasters_podcast_episodes)
    with open(file_path, 'w') as f:
        f.write(output)

def render_location(name, slug, podcasts):
    file_path = os.path.join(CONFIG['OUTPUT_DIR'], slug, "index.html")
    template = env.get_template('location.html')
    output = template.render(name=name, podcasts=podcasts)
    with open(file_path, 'w') as f:
        f.write(output)

def render_podcast_json(podcasts):
    file_path = os.path.join(CONFIG['OUTPUT_DIR'] , "podcasts.js")
    dumper = json.dumps(podcasts)
    with open(file_path, 'w') as f:
        f.write("var podcasts = " + dumper)


# Data Loaders 

def load_location(location):
    file_path = os.path.join(CONFIG['DATA_PATH'] , location)
    with open(file_path) as f:
        urls = f.read().splitlines()
    return urls



# Updated Parser
def parse_location_podcasts(urls):
    podcasts = []
    for url in urls:
        podcast = parse_podcast(url)
        podcasts.append(podcast)
    return podcasts

def download_data(url):
    try:
        response = requests.get(url)
    except requests.exceptions.MissingSchema:
        add_to_fails(url, " Bad URL")
        return None
    if response.status_code is not 200:
        add_to_fails(url, "Returned " + str(response.status_code))
        return None
    return response

def rss_to_dict(data):
    try:
        messy_dict = xmltodict.parse(data.content)
    except:
        return None
    return messy_dict

def get_rss_items(messy_dict):
    try:
        items = messy_dict['rss']['channel']['item']
    except KeyError:
        return None
    return items

def has_enclosures(items):
    for item in items:
        if 'enclosure' in item:
            return True
    return False

def get_last_published(items):
    last_published = None
    if isinstance(items, list):
        for item in items:
            if 'enclosure' in item:
                publishedDate = parsedate_to_datetime(item['pubDate'])
                publishedDate = int(publishedDate.timestamp())
                if last_published is None:
                    last_published = publishedDate
                elif publishedDate > last_published:
                    last_published = publishedDate
    elif isinstance(items, collections.OrderedDict):
        publishedDate = parsedate_to_datetime(items['pubDate'])
        last_published = int(publishedDate.timestamp())
    return last_published


def is_active(last_published):
    if last_published is None:
        return False

    if last_published > deadline:
        return True
    else:
        return False

def get_categories(messy_dict):
    try:
        categories = nested_lookup('@text', messy_dict['rss']['channel']['itunes:category'])
    except KeyError:
        categories = []
    categories = [x.replace("&", "and") for x in categories]
    return categories


def get_description(messy_dict):
    try:
        description = messy_dict['rss']['channel']['itunes:summary']
    except KeyError:
        description = messy_dict['rss']['channel']['description']
    if description is not None:
        description = re.sub('<[^<]+?>', '', description)
    return description

def get_link(messy_dict):
    try:
        link = messy_dict['rss']['channel']['link']
    except KeyError:
        return None
    if link is None:
        return None

    if isinstance(link, list):
        for each in link:
            if isinstance(each, str):
                link = each
                break

    if not link.startswith("http"):
        link = "http://" + link
    return link
        


def parse_podcast(url):
    logger.debug('parsing: ' + url)
    clean_dict = {}
    data = download_data(url)
    if data is None:
        return None

    messy_dict = rss_to_dict(data)
    if messy_dict is None:
        add_to_fails(url, "Could Not Parse")
        return None

    items = get_rss_items(messy_dict)
    if items is None:
        add_to_fails(url, "No Items")
        return None

    if not has_enclosures(items):
        add_to_fails(url, "No Enclosures")
        return None

    clean_dict['link'] = get_link(messy_dict)
    if  clean_dict['link'] is None:
        add_to_fails(url, "Feed Has No Link")
        return None
    clean_dict['lastPublished'] = get_last_published(items)

    clean_dict['active'] = is_active(clean_dict['lastPublished'])
    if clean_dict['active'] is None:
        add_to_fails(url, "Active check failed")
        return None


    clean_dict['categories'] = get_categories(messy_dict)

    clean_dict['description'] = get_description(messy_dict)

    clean_dict['image'] = messy_dict['rss']['channel']['itunes:image']['@href']

    clean_dict['title'] = messy_dict['rss']['channel']['title']
    clean_dict['sortable_tite'] = get_sortable_title(clean_dict['title'])
    clean_dict['slug'] = slugify(clean_dict['title'])
    
    return clean_dict

def get_podcasts(urls):
    podcasts = {}
    podcasts['active'] = []
    podcasts['inactive'] = []
    podcasts['broken'] = []

    for url in urls:
        podcast = parse_podcast(url)
        if podcast is None:
            podcasts['broken'].append(url)
            continue
        if podcast['active']:
            podcasts['active'].append(podcast)
        else:
            podcasts['inactive'].append(podcast)

    podcasts['active'] = sorted(podcasts['active'], key = lambda i: i['sortable_tite']) 
    podcasts['inactive'] = sorted(podcasts['inactive'], key = lambda i: i['sortable_tite']) 

    return podcasts


# Utilities

def get_sortable_title(text):
    articles = ['the ', 'a ', 'an ', 'and ']
    text = text.lower()
    for article in articles:
        if text.startswith(article):
            return text[len(article):]
    return text

#parse_podcast("http://thestorieswetell.libsyn.com/rss")
#exit()

# x = get_sortable_title("The Way with Jazz and Tae")
# print(x)
# exit()


BC_urls = load_location("BritishColumbia")
BC_podcasts = get_podcasts(BC_urls)
render_location("British Columbia", "british_columbia", BC_podcasts)

OR_urls = load_location("Oregon")
OR_podcasts = get_podcasts(OR_urls)
render_location("Oregon", "oregon", OR_podcasts)

WA_urls = load_location("Washington")
WA_podcasts = get_podcasts(WA_urls)
render_location("Washington", "washington", WA_podcasts)

ALL_podcasts = []
ALL_podcasts.extend(BC_podcasts['active'])
ALL_podcasts.extend(OR_podcasts['active'])
ALL_podcasts.extend(WA_podcasts['active'])
ALL_podcasts = sorted(ALL_podcasts, key = lambda i: i['sortable_tite'])

count = 0
for each in ALL_podcasts:
    each['index_id'] = count
    count = count + 1


number_of_podcasts = len(ALL_podcasts)
render_index(number_of_podcasts)
render_podcast_json(ALL_podcasts)
generate_all_cover_art(ALL_podcasts)


# podcasts = get_podcasts()
# number_of_podcasts = len(podcasts)
# render_index(number_of_podcasts)
# render_podcast_json(podcasts)
# generate_all_cover_art(podcasts)


