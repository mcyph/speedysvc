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
        const req = new AjaxRequest("poll");
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