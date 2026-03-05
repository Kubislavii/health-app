let chart = null;

document.addEventListener("DOMContentLoaded", () => {
    const select = document.getElementById("param-select");
    if (!select) return;

    fetch("/api/parameters")
        .then(r => r.json())
        .then(params => {
            params.forEach(p => {
                const opt = document.createElement("option");
                opt.value = p;
                opt.textContent = p;
                select.appendChild(opt);
            });

            // Auto-select parameter from URL hash
            const hash = decodeURIComponent(location.hash.slice(1));
            if (hash && params.includes(hash)) {
                select.value = hash;
                loadChart(hash);
            }
        });

    select.addEventListener("change", () => {
        const param = select.value;
        if (!param) {
            if (chart) { chart.destroy(); chart = null; }
            document.getElementById("no-data").style.display = "none";
            return;
        }
        loadChart(param);
    });
});

function loadChart(parameter) {
    fetch("/api/results/" + encodeURIComponent(parameter))
        .then(r => r.json())
        .then(data => {
            const noData = document.getElementById("no-data");

            if (data.length === 0) {
                if (chart) { chart.destroy(); chart = null; }
                noData.style.display = "block";
                return;
            }
            noData.style.display = "none";

            const labels = data.map(d => d.date);
            const values = data.map(d => d.value);
            const refMin = data[0].ref_min;
            const refMax = data[0].ref_max;
            const unit = data[0].unit;

            const datasets = [
                {
                    label: parameter + " (" + unit + ")",
                    data: values,
                    borderColor: "#2c3e50",
                    backgroundColor: "#2c3e5020",
                    tension: 0.3,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    fill: false,
                }
            ];

            // Reference range as filled area
            if (refMin !== null && refMax !== null) {
                datasets.push({
                    label: "Ref. max (" + refMax + ")",
                    data: labels.map(() => refMax),
                    borderColor: "#ccc",
                    backgroundColor: "transparent",
                    fill: {
                        target: "+1",
                        above: "rgba(200, 200, 200, 0.3)",
                        below: "rgba(200, 200, 200, 0.3)"
                    },
                    pointRadius: 0,
                    borderDash: [5, 5],
                    borderWidth: 1,
                });
                datasets.push({
                    label: "Ref. min (" + refMin + ")",
                    data: labels.map(() => refMin),
                    borderColor: "#ccc",
                    borderDash: [5, 5],
                    borderWidth: 1,
                    backgroundColor: "transparent",
                    fill: false,
                    pointRadius: 0,
                });
            }

            if (chart) chart.destroy();

            chart = new Chart(document.getElementById("chart"), {
                type: "line",
                data: { labels, datasets },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { position: "bottom" },
                        tooltip: {
                            callbacks: {
                                label: ctx => ctx.dataset.label + ": " + ctx.parsed.y
                            }
                        }
                    },
                    scales: {
                        x: { title: { display: true, text: "Datum" } },
                        y: { title: { display: true, text: unit } }
                    }
                }
            });
        });
}
