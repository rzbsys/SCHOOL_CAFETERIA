function clk(num, val) {
    if (val) {
        $('#q' + num + '-N').prop("checked", false);
    } else {
        $('#q' + num + '-Y').prop("checked", false);
    }
}