class Bitrix24 {
    constructor() {
    }

    async callMethod(method, params = {}) {
        return new Promise((resolve, reject) => {
            let callback = result => {
                if (result.status != 200 || result.error()) {
                    console.log(`${result.error()} (callMethod ${method}: ${JSON.stringify(params)})`);
                    return reject("");
                }
                return resolve(result.data());
            };
            BX24.callMethod(method, params, callback);
        });
    }
}


function getRowEventHTML(name, isOffline, handler, connectorId) {
    let typeEventRus = isOffline ? "оффлайн" : "онлайн";
    let typeEventEng = isOffline ? "offline" : "online";
    return `
        <tr data-event="${name}" data-handler="${handler}" data-type="${typeEventEng}" data-connector="${connectorId}">
            <td scope="row">${name}</td>
            <td>${typeEventRus}</th>
            <td>${handler || ""}</td>
            <td>${connectorId || ""}</td>
            <td>
                <div class="table-cell-settings bx24_events__table_events_remove_row">
                    <i class="bi bi-trash bx24_events__table_events_remove_row_i" title="Удалить"></i>
                </div>
            </td>
        </tr>
    `;
}


function generateTbodyHTML(eventsData) {
    let content = '';
    for (let eventData of eventsData) {
        content += getRowEventHTML(eventData.event, eventData.offline, eventData.handler, eventData.connector_id);
    }
    return content
}


function createTable(eventsData) {
    let content = `
        <table class="table table-hover table-bordered caption-top bx24_events__table_events">
            <caption>Список установленных обработчиков событий</caption>
            <thead>
                <tr>
                    <th scope="col">Событие</th>
                    <th scope="col">Тип события</th>
                    <th scope="col">URL обработчика</th>
                    <th scope="col">Коннектор</th>
                    <th scope="col"></th>
                </tr>
            </thead>
            <tbody>
                ${generateTbodyHTML(eventsData)}
            </tbody>
        </table>
    `;
    return content;
}


function getOptionsHTML(eventsList) {
    let contentHTML = '';
    for (let event of eventsList) {
        contentHTML += `<option value="${event}">${event}</option>`;
    }
    return contentHTML;
}


function createAppHTML(contentRegistredTableHTML, eventsList) {
    let content = `
        <style type="text/css">
            .bx24_events__table_events_remove_row {
                width: 100%;
                height: 100%;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .bx24_events__table_events_remove_row i {
                display: inline-block;
                margin: 2px;
                color: #797979;
                font-size: 18px;
                cursor: pointer;
            }
            .bx24_events__table_events_remove_row i::before {
                font-weight: 700 !important;
            }
            .bx24_events__table_events_remove_row i:hover {
                color: #000000;
            }
        </style>
        <div class="bx24_events__table_events_container">
            ${contentRegistredTableHTML}
        </div>

        <div class="bx24_events__registry_event_container">
            <h4>Регистрация событий</h4>
            <div class="border border-1 rounded p-3">
                <div class="bx24_events__type_event">
                    <label for="registry_event__selectTypeEvent" class="form-label">Тип события</label>
                    <select class="form-select bx24_events__registry_event_select" aria-label="Default select example" id="registry_event__selectTypeEvent">
                        <option value="online" selected>Онлайн</option>
                        <option value="offline">Оффлайн</option>
                    </select>
                </div>
                <div class="bx24_events__name_event">
                    <label for="name_event__selectTypeEvent" class="form-label">Название события</label>
                    <select class="form-select" aria-label="Default select example" id="name_event__selectTypeEvent">
                        ${getOptionsHTML(eventsList)}
                    </select>
                </div>
                <div class="bx24_events__handler_event">
                    <label for="name_event__handlerEvent" class="form-label">URL обработчика</label>
                    <input class="form-control" type="text" placeholder="..." aria-label="input example" id="name_event__handlerEvent">
                </div>
                <div class="bx24_events__source_event">
                    <label for="name_event__sourceKey" class="form-label">Ключ источника</label>
                    <input class="form-control" type="text" placeholder="..." aria-label="input example" id="name_event__sourceKey">
                </div>
                <div class="d-grid gap-2 d-md-flex justify-content-md-end mt-2 bx24_events__add_event">
                    <button class="btn btn-primary me-md-2" type="button">Добавить</button>
                </div>
            </div>
        </div>
    `;
    return content;
}


export default class App {
    constructor(container) {
        this.bx = new Bitrix24();                     // объект для выполнения запросов к Битрикс через JS библиотеку
        this.container = container;
        this.eventsList = [];
    }

    async init() {
        this.eventsList = await this.getEventsList();
        // console.log("this.eventsList = ", this.eventsList);
        await this.render();

        this.elemSelectTypeEvent = this.container.querySelector(".bx24_events__type_event select");
        this.elemSelectNameEvent = this.container.querySelector(".bx24_events__name_event select");
        this.elemInputHandlerEvent = this.container.querySelector(".bx24_events__handler_event input");
        this.elemInputSourceEvent = this.container.querySelector(".bx24_events__source_event input");
        this.btnAddEvent = this.container.querySelector(".bx24_events__add_event button");
        this.setOfflineEvent(this.elemSelectTypeEvent.value)

        this.initHandler();
        BX24.fitWindow();
    }

    initHandler() {
        // Удаление зарегистрированного события
        this.container.addEventListener("click", async (e) => {
            let elemRemoveEvent = e.target.classList.contains("bx24_events__table_events_remove_row_i");
            let elemTr = e.target.closest("tr");
            if (elemRemoveEvent && elemTr) {
                let isRemoveEvent = confirm(`Удалить событие \"${elemTr.dataset.event}\"?`);
                if (!isRemoveEvent) return;
                let parameters = {
                    event: elemTr.dataset.event,
                    event_type: elemTr.dataset.type
                };
                if (elemTr.dataset.type == "online") {
                    parameters.handler = elemTr.dataset.handler;
                }
                let resDel = await this.bx.callMethod("event.unbind", parameters);
                if (resDel && resDel.count) {
                    elemTr.remove();
                }
            }
        })

        // Изменение типа события
        this.elemSelectTypeEvent.addEventListener("change", (e) => {
            this.setOfflineEvent(e.target.value);
        })

        // Кнопка содания события
        this.btnAddEvent.addEventListener("click", (e) => {
            this.addEvent();
        })
    }

    async getEventsList() {
        let response = await this.bx.callMethod("events", {});
        // console.log("getEventsList = ", response);
        return response;
    }

    // Регистрирование события
    async addEvent() {
        let isOffline = 0;
        let parameters = {
            event: this.elemSelectNameEvent.value,
            event_type: this.elemSelectTypeEvent.value,
        };
        if (this.elemSelectTypeEvent.value == "online") {
            parameters.handler = this.elemInputHandlerEvent.value;
        } else {
            isOffline = 1
            parameters.auth_connector = this.elemInputSourceEvent.value;
        }
        console.log("Параметры создаваемого события: ", parameters);
        let resAddEvent = await this.bx.callMethod("event.bind", parameters);
        console.log("Результат создания события: ", resAddEvent);
        if (resAddEvent) {
            this.addRecordEventToTable(parameters.event, isOffline, parameters.handler, parameters.auth_connector);
        }
    }

    addRecordEventToTable(eventName, isOffline, eventHandler, eventConnector) {
        this.tBody = this.container.querySelector(".bx24_events__table_events tbody");
        let contentHTML = getRowEventHTML(eventName, isOffline, eventHandler, eventConnector);
        this.tBody.insertAdjacentHTML("beforeend", contentHTML);
    }

    setOfflineEvent(eventType) {
        if (eventType == "offline") {
            this.elemInputHandlerEvent.setAttribute("disabled", "");
            this.elemInputSourceEvent.removeAttribute("disabled");
        } else {
            this.elemInputHandlerEvent.removeAttribute("disabled");
            this.elemInputSourceEvent.setAttribute("disabled", "");
        }
    }

    async render() {
        let events = await this.bx.callMethod("event.get", {});
        // console.log("events = ", events);
        let contentRegistredTableHTML = createTable(events);
        let contentHTML = createAppHTML(contentRegistredTableHTML, this.eventsList);
        this.container.innerHTML = contentHTML;
    }

}



// document.addEventListener("DOMContentLoaded", () => {
//     // BX24.ready(function() {
//         console.log('Start');
//         let container = document.querySelector("#containerEventsManagement");
//         let app = new App(container);
//         app.init();
//     // })
// })
