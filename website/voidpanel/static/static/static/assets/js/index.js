$(function () {
  "use strict";


  // chart 1


  async function loadCSV() {
    const response = await fetch("/static/data.csv");
    const text = await response.text();

    const rows = text.trim().split("\n");
    rows.shift(); // remove header

    let dustValues = rows.map(r => parseFloat(r.split(",")[0]));

    // 🔥 Reduce data to 9 points (like template)
    let step = Math.floor(dustValues.length / 9);
    let reducedData = [];

    for (let i = 0; i < dustValues.length; i += step) {
      reducedData.push(dustValues[i]);
      if (reducedData.length === 9) break;
    }

    drawChart(reducedData);
  }
  function drawChart(dustValues) {

    var options = {
      series: [{
        name: "Dust Value",
        data: dustValues
      }],
      chart: {
        height: 105,
        type: 'area',
        sparkline: { enabled: true }
      },
      stroke: {
        width: 1.7,
        curve: 'smooth'
      },
      fill: {
        type: 'gradient',
        gradient: {
          shade: 'dark',
          gradientToColors: ['#02c27a'],
          opacityFrom: 0.5,
          opacityTo: 0.0
        }
      },
      colors: ["#02c27a"],
      tooltip: { theme: "dark" }
    };

    var chart = new ApexCharts(document.querySelector("#chart1"), options);
    chart.render();
  }

  loadCSV();





  // chart 2

  async function loadPotholeData() {
    const response = await fetch("/static/data.csv");
    const text = await response.text();

    const rows = text.trim().split("\n");
    const header = rows.shift().split(","); // Get headers to find column index

    // Find the index of 'road_label' dynamically
    const roadLabelIndex = header.indexOf("road_label");

    let totalReadings = rows.length;
    let potholeCount = 0;

    // Iterate through rows to count potholes
    rows.forEach(row => {
      const columns = row.split(",");
      if (columns[roadLabelIndex] === "Pothole Detected") {
        potholeCount++;
      }
    });

    // Calculate percentage (e.g., 78%)
    let potholePercentage = totalReadings > 0 ? ((potholeCount / totalReadings) * 100).toFixed(0) : 0;

    // Update the UI text fields
    document.getElementById('total-readings-text').innerText = totalReadings.toLocaleString();
    document.getElementById('pothole-count-text').innerText = potholeCount.toLocaleString();

    drawRadialChart(potholePercentage);
  }

  function drawRadialChart(percentage) {
    var options = {
      series: [percentage],
      chart: {
        height: 230,
        type: 'radialBar',
        toolbar: { show: false }
      },
      plotOptions: {
        radialBar: {
          startAngle: -110,
          endAngle: 110,
          hollow: {
            margin: 0,
            size: '80%',
            background: 'transparent'
          },
          track: {
            background: 'rgba(0, 0, 0, 0.1)',
            strokeWidth: '67%',
          },
          dataLabels: {
            show: true,
            name: { show: false },
            value: {
              offsetY: 10,
              color: '#fff', // White text for dark theme
              fontSize: '24px',
              show: true,
              formatter: function (val) {
                return val + "%";
              }
            }
          }
        }
      },
      fill: {
        type: 'gradient',
        gradient: {
          shade: 'dark',
          type: 'horizontal',
          shadeIntensity: 0.5,
          gradientToColors: ['#0866ff'],
          inverseColors: true,
          opacityFrom: 1,
          opacityTo: 1,
          stops: [0, 100]
        }
      },
      colors: ["#fc185a"],
      stroke: {
        lineCap: 'round'
      },
      labels: ['Pothole Ratio'],
    };

    var chart = new ApexCharts(document.querySelector("#chart2"), options);
    chart.render();
  }

  // Initialize
  loadPotholeData();



  // chart 3


  async function loadCSVForBar() {
    const response = await fetch("/static/data.csv");
    const text = await response.text();

    const rows = text.trim().split("\n");
    rows.shift(); // remove header

    let potholeCount = 0;
    let smoothCount = 0;

    rows.forEach(row => {
      const cols = row.split(",");
      const roadLabel = cols[4]; // road_label column

      if (roadLabel === "Pothole Detected") potholeCount++;
      if (roadLabel === "Smooth Road") smoothCount++;
    });

    document.getElementById("totalReadings").innerText = rows.length;

    drawBarChart(potholeCount, smoothCount);
  }
  function drawBarChart(potholeCount, smoothCount) {

    // Create visual bar pattern (like second image)
    const data = [
      potholeCount * 0.3,
      potholeCount * 0.5,
      potholeCount * 0.8,
      potholeCount,
      smoothCount,
      smoothCount * 0.8,
      smoothCount * 0.6,
      smoothCount * 0.4,
      smoothCount * 0.2
    ];

    var options = {
      series: [{
        name: "Road Events",
        data: data
      }],
      chart: {
        type: 'bar',
        height: 150,
        sparkline: { enabled: true },
        toolbar: { show: false }
      },
      plotOptions: {
        bar: {
          columnWidth: '35%',            // 🔥 slim bars
          borderRadius: 6,
          borderRadiusApplication: 'end' // 🔥 round top only
        }
      },
      fill: {
        type: 'gradient',
        gradient: {
          type: 'vertical',
          shadeIntensity: 0,
          gradientToColors: ['#ff7a18'], // orange top
          opacityFrom: 1,
          opacityTo: 1,
          stops: [0, 100]
        }
      },
      colors: ['#ff0066'], // pink base
      dataLabels: { enabled: false },
      tooltip: { enabled: false },
      grid: { show: false },
      xaxis: { labels: { show: false } },
      yaxis: { show: false }
    };

    document.querySelector("#chart3").innerHTML = "";
    new ApexCharts(document.querySelector("#chart3"), options).render();
  }


  loadCSVForBar();



  // chart 4

  async function loadChart4Data() {
    const response = await fetch("/static/data.csv");
    const text = await response.text();

    const rows = text.trim().split("\n");
    rows.shift(); // remove header

    // Map both columns: Dust (Index 0) and Accel_Z (Index 3)
    let dustValues = rows.map(r => parseFloat(r.split(",")[0]));
    let vibrationValues = rows.map(r => Math.abs(parseFloat(r.split(",")[3])) / 1000); // Normalized for chart

    // 🔥 Reduce data to 9 points to match the 'Jan' to 'Sep' categories
    let step = Math.floor(rows.length / 9);
    let reducedDust = [];
    let reducedVibration = [];

    for (let i = 0; i < rows.length; i += step) {
      reducedDust.push(dustValues[i]);
      reducedVibration.push(reducedVibration.length === 0 ? vibrationValues[i] : vibrationValues[i].toFixed(1));
      if (reducedDust.length === 9) break;
    }

    drawChart4(reducedDust, reducedVibration);
  }

  function drawChart4(dustData, vibData) {
    var options = {
      series: [{
        name: "Vibration",
        data: vibData
      },
      {
        name: "Dust Value",
        data: dustData
      }],
      chart: {
        foreColor: "#9ba7b2",
        height: 260,
        type: 'bar',
        toolbar: { show: false },
        zoom: { enabled: false }
      },
      dataLabels: { enabled: false },
      stroke: {
        width: 4,
        colors: ['transparent']
      },
      fill: {
        type: 'solid', // Simplified for reliability
        opacity: [1, 0.35]
      },
      colors: ['#0d6efd', "#0d6efd"], // Blue and Light Blue
      plotOptions: {
        bar: {
          horizontal: false,
          borderRadius: 4,
          columnWidth: '55%',
        }
      },
      grid: {
        show: false
      },
      tooltip: {
        theme: "dark",
      },
      xaxis: {
        categories: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep'],
      }
    };

    var chart = new ApexCharts(document.querySelector("#chart4"), options);
    chart.render();
  }

  // Initialize the chart load
  loadChart4Data();





  // chart 5

  var options = {
    series: [{
      name: "Net Sales",
      data: [4, 10, 25, 12, 25, 18, 40, 22, 7]
    }],
    chart: {
      //width:150,
      height: 115,
      type: 'area',
      sparkline: {
        enabled: !0
      },
      zoom: {
        enabled: false
      }
    },
    dataLabels: {
      enabled: false
    },
    stroke: {
      width: 1.7,
      curve: 'smooth'
    },
    fill: {
      type: 'gradient',
      gradient: {
        shade: 'dark',
        gradientToColors: ['#6610f2'],
        shadeIntensity: 1,
        type: 'vertical',
        opacityFrom: 0.5,
        opacityTo: 0.0,
        //stops: [0, 100, 100, 100]
      },
    },

    colors: ["#6610f2"],
    tooltip: {
      theme: "dark",
      fixed: {
        enabled: !1
      },
      x: {
        show: !1
      },
      y: {
        title: {
          formatter: function (e) {
            return ""
          }
        }
      },
      marker: {
        show: !1
      }
    },
    xaxis: {
      categories: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep'],
    }
  };

  var chart = new ApexCharts(document.querySelector("#chart5"), options);
  chart.render();





});