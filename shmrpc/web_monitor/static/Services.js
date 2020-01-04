/*jshint esversion: 6 */
"use strict";

class Services {
    constructor() {
        /*
        A class that keeps track of all the services,
        polling for updates for them all via AJAX.
         */
        this.pollPeriodically = this.pollPeriodically.bind(this);
        this.pollPeriodically();
    }

    pollPeriodically() {
        // TODO:
        // * Only poll time series data if it's expanded
        // * Get the updated console data based on the current offset
        // * Only show method average execution times/number of calls if expanded
        //   (after implementing this functionality!)

        const req = new AjaxRequest("poll", {offset: this.getConsoleOffset()});
        req.send(function(DServices) {
            document.getElementById("service_status_table_cont").innerHTML =
                DServices["service_table_html"];

            if (DServices["console_text"]) {
                document.querySelector(".console_log").innerHTML +=
                    DServices["console_text"];
            }
            document.querySelector(".console_log").setAttribute(
                "offset", DServices["console_offset"]
            );
        }, function() {

        });

        // Poll once every 3 secs, in line with data
        setTimeout(this.pollPeriodically, 2000);
    }

    getConsoleOffset() {
        return parseInt(
            this.$(".console_log").getAttribute("offset")
        );
    }
}
