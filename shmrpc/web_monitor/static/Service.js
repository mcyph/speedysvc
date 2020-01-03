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

    pollPeriodically() {
        // TODO:
        // * Only poll time series data if it's expanded
        // * Get the updated console data based on the current offset
        // * Only show method average execution times/number of calls if expanded
        //   (after implementing this functionality!)

        const req = new AjaxRequest("poll_service_info", {
            port: this.port,
            console_offset: this.getConsoleOffset()
        });
        const that = this;

        req.send(function(o) {
            for (let port in o) {
                that.DServices[port].update(o[port]);
            }
        }, function() {

        });

        // Poll once every 3 secs, in line with data
        setTimeout(this.pollPeriodically, 3000);
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
