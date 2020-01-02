/*jshint esversion: 6 */
"use strict";

class Services {
    constructor(LServices) {
        /*
        A class that keeps track of all the services,
        polling for updates for them all via AJAX.
         */
        this.DServices = {};
        this.LServices = [];
        for (let [serviceName, port] of LServices) {
            const elm = document.getElementById(
                `service_cont_div_${port}`
            );
            var service = new Service(serviceName, port, elm);
            this.LServices.push(service);
            this.DServices[port] = service;
        }
        this.pollPeriodically = this.pollPeriodically.bind(this);
        this.pollPeriodically();
    }

    pollPeriodically() {
        // TODO:
        // * Only poll time series data if it's expanded
        // * Get the updated console data based on the current offset
        // * Only show method average execution times/number of calls if expanded
        //   (after implementing this functionality!)

        const offsets = {};
        for (let service of this.LServices) {
            offsets[service.port] = service.getConsoleOffset();
        }
        const req = new AjaxRequest("poll", {offsets: JSON.stringify(offsets)});
        const that = this;

        req.send(function(o) {
            for (let port in o) {
                that.DServices[port].update(o[port]);
            }
        }, function() {

        });

        // Poll once every 5 secs, in line with data
        setTimeout(this.pollPeriodically, 5*1000);
    }
}
