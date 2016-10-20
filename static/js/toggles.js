/**
 * Created by yannis on 10/6/2016.
 */

function toggle_buttons(container, compost_id) {
    //$(container).click(function () {
    if ($(container).hasClass('btn-success')) {
        $(container).removeClass('btn-success');
        $(container).addClass('btn-danger');
        $(container).html('OFF');
        $.post('/compost_controls', {id: compost_id, control: container, state: 'OFF'}).success(function () {
                location.reload();
                //location.href = "/change_compost/Compost_Ilioupoli"
            });
        //console.log(container);
    } else {
        $(container).removeClass('btn-danger');
        $(container).addClass('btn-success');
        $(container).html('ON');
        $.post('/compost_controls', {id: compost_id, control: container, state: 'ON'}).success(function () {
                location.reload();
                //location.href = "/change_compost/Compost_Ilioupoli"
            });
    }
}

function update_button(container, c_state) {
    $.ajax({
        type: 'POST',
        url: '/compost_controls',
        data: {control: container, state: c_state},
        success: function () {
            location.reload();
        }
    });
}
