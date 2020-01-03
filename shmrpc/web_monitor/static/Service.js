/*jshint esversion: 6 */
"use strict";

class Service {
    constructor(serviceName, port, elm) {
        /*
        A class representing a kind of server
         */
        this.serviceName = serviceName;
        this.port = port;
        this.elm = elm;
    }

    $(selector) {
        return this.elm.querySelector(selector);
    }

    getConsoleOffset() {
        return parseInt(
            this.$(".console_log").getAttribute("offset")
        );
    }

    //======================================================//
    // Start/stop/restart
    //======================================================//

    stop() {
        new AjaxRequest(
            "stop_service", {port: this.port}
        ).send();
    }
    start() {
        new AjaxRequest(
            "start_service", {port: this.port}
        ).send();
    }
    restart() {
        new AjaxRequest(
            "restart_service", {port: this.port}
        ).send();
    }

    //======================================================//
    // Base update methods
    //======================================================//

    update(o) {
        this.updateStatusTable(o["table_html"]);
        this.updateGraphs(o["graphs"]);

        if (o["console_text"]) {
            this.writeConsoleHTML(o["console_text"]);
        }
    }

    updateStatusTable(tableHTML) {
        this.$(
            ".status_table_cont_div"
        ).innerHTML = tableHTML;
    }

    //======================================================//
    // Graphs
    //======================================================//

    updateGraphs(o) {
        if (!this.graphsInit) {
            this.ramGraph = new LineChart(
                this.$(".ram_chart").firstChild, o["labels"], o["ram"]
            );
            this.cpuGraph = new LineChart(
                this.$(".cpu_chart").firstChild, o["labels"], o["cpu"]
            );
            this.ioGraph = new LineChart(
                this.$(".io_chart").firstChild, o["labels"], o["io"]
            );
            this.graphsInit = true;
        }
        else {
            this.ramGraph.update(o["labels"], o["ram"]);
            this.cpuGraph.update(o["labels"], o["cpu"]);
            this.ioGraph.update(o["labels"], o["io"]);
        }
    }

    //======================================================//
    // Console Text
    //======================================================//

    writeConsoleHTML(html) {
        this.$(".console_log").innerHTML += html;
    }
}
