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

        const req = new AjaxRequest("poll");
        req.send(function(serviceHTML) {
            document.getElementById("service_status_table_cont").innerHTML = serviceHTML;
        }, function() {

        });

        // Poll once every 3 secs, in line with data
        setTimeout(this.pollPeriodically, 2000);
    }
}
