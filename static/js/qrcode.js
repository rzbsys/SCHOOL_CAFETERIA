
var EXPIRE_TIME = 0;
var timer, Start_Time, now, extend_timer, before_value, after_value;

function min(a, b) {
    return a > b ? b : a;
}

function zero(a) {
    if (a < 10) {
        return '0' + a;
    } else {
        return a;
    }
}

function refresh() {
    clearInterval(timer);
    clearInterval(extend_timer);
    $('.left-time').text('새로고침');
    get_token();
}

function extended_check() {
    $('.left-time').text('새로고침 대기중');
    before_value = now;
    $.ajax({
        url: '/getusertoken',
        type: 'POST',
        success: function (data) {
            after_value = data['res'];
            if (after_value != before_value) {
                clearInterval(extend_timer);
                refresh();
            }
        },
        error: function (err) {
            $('.left-time').text('새로고침 실패');
        }
    }); 
}

function check_refresh() {
    var Now = new Date;
    var Cal_time = parseInt((Now.getTime() - Start_Time.getTime()) / 1000);
    var left_min = parseInt((EXPIRE_TIME - Cal_time) / 60);
    var left_sec = parseInt((EXPIRE_TIME - Cal_time) % 60);
    $('.left-time').text(zero(left_min) + ':' + zero(left_sec));
    if (left_min <= 0 && left_sec <= 0) {
        $('.left-time').text('새로고침 대기중');
        clearInterval(timer);
        extend_timer = setInterval(extended_check, 5000);
    }
}

function get_token() {
    $.ajax({
        url: '/getusertoken',
        type: 'POST',
        success: function (data) {
            Start_Time = new Date();
            const Date_info = data['expire'].split(' ');
            const Hour_Min_Sec = Date_info[4].split(':')
            Start_Time.setHours(parseInt(Hour_Min_Sec[0]));
            Start_Time.setMinutes(parseInt(Hour_Min_Sec[1]));
            Start_Time.setSeconds(parseInt(Hour_Min_Sec[2]));        
            now = data['res'];
            EXPIRE_TIME = data['duration'];
            
            $('#qrcode').empty();
            new QRCode(document.getElementById("qrcode"), {
                text: now,
                width: min($('.qr-box').width() - 70, 300),
                height: min($('.qr-box').width() - 70, 300),
                colorDark: "#000000",
                colorLight: "#ffffff",
                correctLevel: QRCode.CorrectLevel.H
            });

            timer = setInterval(check_refresh, 1000);
        },
        error: function (err) {
            alert('서버와 통신할 수 없습니다.');
        }
    }); 
}



get_token();