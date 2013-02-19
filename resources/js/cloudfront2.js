// Main loader for CF2.

if (typeof console === "undefined" || typeof console.log === "undefined") {
  console = {};
  console.log = function() {};
}

var Atmo = {
  Collections: {
    New: {
      Test: {}
    },
  },
  Models: {
    New: {}
  },
  New: {},
  Templates: {},
  Utils: {},
  Views: {}
};

/* Size elements appropriately when the screen size changes */
function resizeApp() {
	//console.log($(window).width());
	if ($(window).width() > 768) {

		var sidebar_target_height = $('#sidebar').outerHeight() - $('#menu_atmo_title').outerHeight() - $('#new_instance_link').outerHeight(); /* Account for padding and margins */
		var sidebar_link_list_title_height = $('.link_list_title').outerHeight() * $('.link_list_title').length;
        //console.log('RESIZE APP', sidebar_target_height, sidebar_link_list_title_height);
		$('#instance_link_list, #volume_link_list').css('max-height', (sidebar_target_height - sidebar_link_list_title_height)  / 2);

		$('#image_holder').height($('#content').height() - $('#image_header').outerHeight() - $('#image_search_holder').outerHeight() - $('#selected_image_info_container h1').outerHeight() - 45);

		$('.shell_iframe').height($('#content').height() - $('#resource_usage_title').outerHeight() - $('#resource_usage_holder').outerHeight() - $('.instance_tabs:visible').outerHeight() - 110);
		$('.vnc_iframe').height($('#content').height() - $('#resource_usage_title').outerHeight() - $('#resource_usage_holder').outerHeight() - $('.instance_tabs:visible').outerHeight() - 110);
		$('#selected_image').height($('#content').height() - $('#logged_in_data').height() - $('#image_header').height());

		$('#draggable_container').height(
			$('#content').height() - 
			$('#volume_header').height() -
			$('#volume_controls').height() - 140
		);


	} else {
        $('#instance_link_list, #volume_link_list').css('max-height', 'auto');
	}
}
        
$(document).ready(function() {
  // Scale necessary divs
  resizeApp();
  // This is a hack
  setTimeout(resizeApp, 1000);
});
$(window).resize(resizeApp);

/* Allow Capitalization of strings */
String.prototype.capitalize = function() {
  return this.replace(/(?:^|\s)\S/g, function(a) { return a.toUpperCase(); });
};
/* Allow Finding strings */
String.prototype.find = function(needle) {
  return this.indexOf(needle) > -1;
};

/** CUSTOM SELECTORS */
//icontains - Case Insensitive Contains
$.expr[":"].icontains = function(obj, i, m) {
  return icontains(m[3], $(obj).text());
}

function icontains(needle, haystack) {
	var found = false;

	if(!needle) return found;

	//SANITIZE SEARCH
	needle = needle.replace(/\//gi, "\\/");//Replace all / with \/
	needle = needle.replace(/\+/gi, "\\+");//Replace all + with \+
	needle = needle.replace(/\[/gi, "\\[");//Replace all + with \+
	needle = needle.replace(/\]/gi, "\\]");//Replace all + with \+

	//Test if contained in object text (Name)
	found = found || eval("/"+needle+"/i").test(haystack);

	if(found)
		//console.log("Matched on Text");
	
	return found;
}

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
var csrftoken = getCookie('csrftoken');

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

$.ajaxSetup({
    crossDomain: false,
    beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type)) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});

