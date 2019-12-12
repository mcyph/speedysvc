/*jshint esversion: 6 */
"use strict";

function encParams(params) {
    return Object.entries(params).map(
        kv => kv.map(encodeURIComponent).join("=")
    ).join("&");
}

class AjaxRequest {
    constructor(url, params) {
        /*
        Create a new AJAX GET request to url,
        optionally encoding ?key=value params.
        Sends to callback only on success:
            errors not handled.
         */
        if (params) {
            params = encParams(params);
            url = "${url}?${params}";
        }
        const that = this;
        const xhr = this.xhr = new XMLHttpRequest();
        xhr.onreadystatechange = function() {
            if (xhr.readyState === 4){
                that.onSuccess(JSON.parse(xhr.responseText));
            }
            else {
                // TODO!
            }
        };
        xhr.open("GET", url);
    }
    send(onSuccess, onError) {
        this.onSuccess = onSuccess;
        this.onError = onError;
        this.xhr.send();
    }
}
