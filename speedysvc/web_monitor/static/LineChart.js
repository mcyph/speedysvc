/*jshint esversion: 6 */
"use strict";

class LineChartDataset {
    constructor(label, data, backgroundColor, borderColor) {
        this.label = label; // e.g.
        this.data = data;
        this.backgroundColor = backgroundColor;
        this.borderColor = borderColor || backgroundColor;
    }
}

function listToLineChartDataset(L) {
    return L.map(i => new LineChartDataset(
        i[0], i[1], i[2], i[3]
    ));
}

class LineChart {
    constructor(elm, labels, datasets) {
        if (!(datasets instanceof LineChartDataset)) {
            datasets = listToLineChartDataset(datasets);
        }

        var ctx = elm.getContext("2d");

        this.chart = new Chart(ctx, {
            // The type of chart we want to create
            type: "line",

            // The data for our dataset
            data: {
                labels: labels,
                datasets: datasets
            },

            // Configuration options go here
            options: {animation: false}
        });
    }

    update(labels, datasets) {
        if (!(datasets instanceof LineChartDataset)) {
            datasets = listToLineChartDataset(datasets);
        }

        this.chart.data.labels = labels;
        this.chart.data.datasets = datasets;
        this.chart.update();
    }
}
