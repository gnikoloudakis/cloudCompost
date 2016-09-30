/**
 * Created by yannis on 4/21/2016.
 */

var map,infowindow, marker;


function create_map(user_location) {
    map = new google.maps.Map(document.getElementById('map'), {
        zoom: 12,
        center: new google.maps.LatLng(user_location[0], user_location[1]),
        mapTypeId: google.maps.MapTypeId.ROADMAP
    });
}

function set_user_marker(user_location){
    marker = new google.maps.Marker({
            position: new google.maps.LatLng(user_location[0], user_location[1]),
            map: map,
            icon: 'http://maps.google.com/mapfiles/kml/paddle/red-circle.png'
        });
}
function set_markers(locations){
    infowindow = new google.maps.InfoWindow();

    var i;

    for (i = 0; i < locations.length; i++) {
        marker = new google.maps.Marker({
            position: new google.maps.LatLng(locations[i][1], locations[i][2]),
            map: map,
            icon: 'http://maps.google.com/mapfiles/kml/paddle/blu-circle.png'
        });

        google.maps.event.addListener(marker, 'click', (function (marker, i) {
            return function () {
                infowindow.setContent(locations[i][0]);
                infowindow.open(map, marker);
            }
        })(marker, i));
    }
}