/**
 * Created by yannis on 10/6/2016.
 */

function toggle_buttons(container) {
    //$(container).click(function () {
    if ($(container).hasClass('btn-success')) {
        $(container).removeClass('btn-success');
        $(container).addClass('btn-danger');
        $(container).html('OFF');
        //update_button(compost_id, container, 'OFF');
        $.post('/compost_controls', {control: container, state: 'ON'}).success(function () {
                location.reload();
            });
        //console.log(container);
    } else {
        $(container).removeClass('btn-danger');
        $(container).addClass('btn-success');
        $(container).html('ON');
        //update_button(compost_id, container, 'ON');
        $.post('/compost_controls', {control: container, state: 'ON'}).success(function () {
                location.reload();
            });
    }
}

function update_button(compost_id, container, c_state) {
    $.ajax({
        type: 'POST',
        url: '/compost_controls',
        data: {compost_id: compost_id, control: container, state: c_state}
    });
}
