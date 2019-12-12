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
            const elm = document.getElementById("${port}");
            this.LServices.push(new Service(serviceName, port, elm));
            this.DServices[port] = FIXME;
        }
        this.pollPeriodically();
    }

    pollPeriodically() {
        const req = new AjaxRequest("poll");

        req.send(function(o) {
            for (let port of o) {
                this.DServices[port].update(o);
            }
        }, function() {

        });

        // Poll once every 5 secs, in line with data
        setTimeout(this.pollPeriodically, 5*1000);
    }
}
