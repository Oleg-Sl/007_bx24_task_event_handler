import App from './change_events.js';                                                                     // модуль выполнения работы к Битрикс

document.addEventListener("DOMContentLoaded", () => {
    BX24.ready(function() {
        console.log('Start');
        let container = document.querySelector("#containerEventsManagement");
        let app = new App(container);
        app.init();
    })
})
