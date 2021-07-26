$(() => {
    const tmpl = $.templates("#msg-template");
    const append = (text, pos) => $("#msgs").append(tmpl.render({text, pos}));

    const socket = io();

    socket.on('data', msg => append(msg, "start"));

    $("#send-btn").click(() => {
        let text = $("#send-text").val();
        append(text, "end");
        socket.emit('data', text);
    });
});
