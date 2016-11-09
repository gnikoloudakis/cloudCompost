/**
 * Created by yannis on 10/5/2016.
 */
/**
 * Request data from the server, add it to the graph and set a timeout
 * to request again
 */
function requestData(delay) {
    $.ajax({
        url: '/measurements',
        success: function (point) {
            var series = chart.series[0],
                shift = series.data.length > 600; // shift if the series is
            // longer than 20

            // add the point
            chart.series[0].addPoint([point.m_timestamp.$date, point.m_value], true, shift);

            // call it again after one second
            setTimeout(requestData, 1000);
        },
        cache: false
    });
}

function new_chart(container, type, m_type, title, series_text, mdelay) {
    chart = new Highcharts.Chart({
        chart: {
            renderTo: container,
            defaultSeriesType: type,
            animation: Highcharts.svg, // don't animate in old IE
            marginRight: 10,
            events: {
                load: function () {
                    var series = this.series[0],
                        shift = series.data.length > 600; // shift if the series is
                    setInterval(function () {
                        $.ajax({
                            type: 'POST',
                            url: '/measurements',
                            data: {m_type: 'soil_hum'},
                            success: function (m_data) {
                                series.addPoint([m_data.m_timestamp.$date, m_data.m_value], true, shift);
                            }
                        })
                    }, mdelay);
                }
            }
        },
        title: {
            text: title
        },
        xAxis: {
            type: 'datetime',
            tickPixelInterval: 150,
            maxZoom: 20 * 1000
        },
        yAxis: {
            minPadding: 0.2,
            maxPadding: 0.2,
            title: {
                text: 'Value',
                margin: 80
            }
        },
        tooltip: {
            formatter: function () {
                return '<b>' + this.series.name + '</b><br/>' +
                    Highcharts.dateFormat('%Y-%m-%d %H:%M:%S', this.x) + '<br/>' +
                    Highcharts.numberFormat(this.y, 2);
            }
        },
        series: [{
            name: series_text,
            data: []
        }]
    });
}


function dummy_chart(container) {
    $.post('/preliminary/measurements', {m_type: 'soil_hum'}, function (m_data) {
        var series = [];
        var len = m_data.length;
        console.log(len);
        for (var i = len - 10; i < len; i++) {
            series.push([m_data[i].m_timestamp.$date, m_data[i].m_value]);
        }

        console.log(series);
        $(container).highcharts({
            chart: {
                type: 'spline',
                animation: Highcharts.svg, // don't animate in old IE
                //marginRight: 10,
                events: {
                    load: function () {
                        var series = this.series[0],
                            shift = series.data.length > 10; // shift if the series is
                        //console.log(series.data.length);
                        setInterval(function () {
                            shift = series.data.length > 10;
                            //console.log(series.data.length);
                            $.ajax({
                                type: 'POST',
                                url: '/measurements',
                                data: {m_type: 'soil_hum'},
                                success: function (m_data) {
                                    series.addPoint([m_data.m_timestamp.$date, m_data.m_value], true, true);
                                    //series.push([m_data.m_timestamp.$date, m_data.m_value]);
                                    console.log(m_data.m_value);
                                }
                            })
                        }, 5000);
                    }
                }
            },

            title: {
                text: 'title'
            },
            xAxis: {
                type: 'dateTime',
                tickPixelInterval: 150
            },
            yAxis: {
                title: {
                    text: 'yaxis'
                }
                //max: 50
            },
            tooltip: {
                formatter: function () {
                    return Highcharts.dateFormat('%d/%m/%Y %H:%M:%S', this.x) + '<br/> <b>' +
                        Highcharts.numberFormat(this.y, 1) + '°C</b>';
                }
            },
            plotOptions: {
                area: {
                    marker: {
                        radius: 1
                    },
                    lineWidth: 1,
                    states: {
                        hover: {
                            lineWidth: 1
                        }
                    },
                    threshold: null
                }
            },
            exporting: {
                enabled: true
            },
            series: [{
                name: 'Temperature',
                data: series
            }]
        });
    });
}

//var wdata = [];
function create_chart(container, type, mtype, title, seriestext, xaxis, yaxis, delay) {
    var wdata = [];
    var state = false;
    var socket = io.connect();

    $.post('/preliminary/measurements', {m_type: mtype})
        .done(function (m_data) {
            //socket.emit('preliminary_measurements', {m_type: mtype});
            //socket.on('preliminary_return', function(q_data){
            //        var m_data = JSON.parse(qdata);
            if (m_data.length != 0) {
                console.log(mtype);
                for (var i = 0; i < m_data.length; i++) {

                    //console.log(m_data[i].m_value);
                    //console.log(Date(m_data[i].m_timestamp.$date));
                    if (m_data[i].m_value) {
                        //console.log(m_data[i].m_value, m_data[i].m_timestamp.$date);
                        wdata.push({
                                x: m_data[i].m_timestamp.$date,
                                y: m_data[i].m_value
                            }
                        );
                    }
                    else {
                        wdata.push({
                                x: i,
                                y: i + 0.1
                            }
                        );
                    }
                }
            }
            else {
                wdata.push({
                        x: 0,
                        y: 0
                    }
                );
            }
            //console.log(wdata);
            $(container).highcharts({
                chart: {
                    type: type,
                    animation: Highcharts.svg, // don't animate in old IE
                    marginRight: 10,
                    zoomType: 'x',
                    events: {
                        load: function () {
                            // set up the updating of the chart each second
                            var series = this.series[0];
                            setInterval(function () {
                                //console.log(wdata.length);
                                if (wdata.length >= 50) {
                                    state = true;
                                }
                                var x = (new Date()).getTime(), // current time
                                    y = Math.random();
                                $.post('/measurements', {m_type: mtype}).done(function (wwww) {
                                    series.addPoint([wwww.m_timestamp.$date, wwww.m_value], true, state);
                                });

                            }, 10000);
                        }
                    }
                },
                title: {
                    text: title
                },
                xAxis: {
                    type: 'datetime',
                    tickPixelInterval: 150
                },
                yAxis: {
                    title: {
                        text: yaxis
                    },
                    plotLines: [{
                        value: 0,
                        width: 1,
                        color: '#808080'
                    }]
                },
                tooltip: {
                    formatter: function () {
                        return '<b>' + this.series.name + '</b><br/>' +
                            Highcharts.dateFormat('%Y-%m-%d %H:%M:%S', this.x) + '<br/>' +
                            Highcharts.numberFormat(this.y, 2);
                    }
                },
                legend: {
                    enabled: false
                },
                exporting: {
                    enabled: false
                },
                series: [{
                    name: seriestext,
                    data: wdata
                }]
            });
        });
}