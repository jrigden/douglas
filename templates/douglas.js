
document.addEventListener('keyup', function (event) { 
    if (event.keyCode === 13) {
        makeSearchURL();

    }

});

//Handlebars Helpers
Handlebars.registerHelper ('truncate', function (str, len) {
    if (str.length > len) {
        var new_str = str.substr (0, len+1);

        while (new_str.length) {
            var ch = new_str.substr ( -1 );
            new_str = new_str.substr ( 0, -1 );

            if (ch == ' ') {
                break;
            }
        }

        if ( new_str == '' ) {
            new_str = str.substr ( 0, len );
        }

        return new Handlebars.SafeString ( new_str +'...' ); 
    }
    return str;
});


var podcast_source   = document.getElementById("podcast-template").innerHTML;
var podcast_template = Handlebars.compile(podcast_source);
var defaultMessageHeader = document.getElementById("message-header").innerHTML;
var defaultMessageMessage = document.getElementById("message-message").innerHTML



//Routing
function locationCheck() {
    //console.log("locationCheck")
    //console.log(location.hash)

    if (location.hash.startsWith("#/category/")) {
        hideMasthead();
        clearPodcasts();
        var category = location.hash.replace("#/category/", "");
        category = decodeURI(category);
        render_category(category);
        window.scrollTo(0, 0);
    }
    else if (location.hash.startsWith("#/search/")) {
        hideMasthead();
        clearPodcasts();
        var query = location.hash.replace("#/search/", "");
        query = decodeURI(query);
        render_search(query)
        window.scrollTo(0, 0);

    }

    else {
        clearPodcasts();
        showMasthead();
        changeMessage(defaultMessageHeader, defaultMessageMessage)
        console.log("home");
        window.scrollTo(0, 0);
    }

}

window.onhashchange = locationCheck;

window.onload = function() {
    locationCheck();
};

//Message Section

function changeMessage(header, message){
    document.getElementById("message-header").innerHTML =  header;
    document.getElementById("message-message").innerHTML =  message;

}

//Masthead
function hideMasthead() {
    document.getElementById("masthead").classList.add("hide")
}

function showMasthead() {
    document.getElementById("masthead").classList.remove("hide")
}


//Podcast Section
function clearPodcasts(){
    document.getElementById("podcasts-section").innerHTML = ""
    
}




// Reder Podcasts
function render_selected_podcasts(selected_podcasts) {
    clearPodcasts();
    var temp_html = ""
    var active_podcasts = []
    var inactive_podcasts = []
    selected_podcasts.forEach(function(podcast) {
        if (podcast.active) {
            active_podcasts.push(podcast)
        } else {
            inactive_podcasts.push(podcast)
        }
    });

    if (active_podcasts.length > 0) {
        active_podcasts.forEach(function(podcast) {
            var context = podcast;
            var podcast_html    = podcast_template(context)
            temp_html = temp_html + podcast_html
        });
    }

    document.getElementById("podcasts-section").innerHTML = temp_html;
}

// Search



function makeSearchURL(){
    var query  = document.getElementById("search-input").value;
    if (query == "") {
        return
    }
    var encoded_query = encodeURI(query);
    console.log(encoded_query);
    window.location.href = "/#/search/" + encoded_query;
}


// Lucky
function luckyPodcast(){
    var podcast = podcasts[Math.floor(Math.random() * podcasts.length)];
    console.log(podcast.link);
    window.location.href = podcast.link, true;
    return false;

}

// Categories

function render_category(category) {
    var selected_podcasts = [];
    podcasts.forEach(function(podcast) {
        if (podcast.categories.includes(category)) {
            selected_podcasts.push(podcast)
        }        
    });
    if (selected_podcasts.length == 0) {
        changeMessage("<h2>No Podcasts in the <strong>" + category + "</strong> Category</h2>", " ")

    } else {
        changeMessage("<h2>Podcasts in the <strong>" + category + "</strong> Category</h2>", " ")
        //document.getElementById("podcasts-section").innerHTML = selected_podcasts
        render_selected_podcasts(selected_podcasts)
    }
}

// Search

var idx = lunr(function () {
    this.ref('index_id')
    this.field('title')
    this.field('description')
    
podcasts.forEach(function (doc) {
        this.add(doc)
    }, this)
})

function render_search(query){
    changeMessage('<h2>Podcasts with the term <strong>"' + query + '"</strong></h2>', ' ')
    var selected_podcasts = [];
    results = idx.search(query);
    results.forEach(function(result) {
        selected_podcasts.push(podcasts[result.ref])

    });
    render_selected_podcasts(selected_podcasts);
}