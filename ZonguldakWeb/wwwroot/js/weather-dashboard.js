// weather-dashboard.js

// Grafik çizen fonksiyon
function grafikCiz(veri) {
    if (!veri) {
        console.error('Veri yok!');
        return;
    }

    var options = {
        series: veri.series,
        chart: {
            height: 450,
            type: 'line',
            background: 'transparent'
        },
        stroke: {
            width: [2, 2, 2, 2, 4, 2],
            dashArray: [0, 0, 0, 0, 0, 5],
            curve: 'smooth'
        },
        colors: ['#00e7ff', '#ffa500', '#ff0000', '#00ff00', '#2b57f5', '#a0a0a0'],
        xaxis: {
            categories: veri.categories
        },
        annotations: {
            yaxis: [{
                y: -6,
                borderColor: '#9C27B0',
                label: {
                    style: { color: '#fff', background: '#9C27B0' },
                    text: 'KAR SINIRI (-6°C)'
                }
            }]
        }
    };

    var chart = new ApexCharts(document.querySelector("#chart"), options);
    chart.render();
}

// Tarihsel analiz yükleyen fonksiyon
function tarihselAnalizYukle() {
    var container = document.getElementById('tarihsel-alan');
    
    fetch('/Home/TarihselAnalizGetir')
        .then(function(response) {
            return response.text();
        })
        .then(function(data) {
            var formatted = data
                .replace(/\n/g, "<br>")
                .replace(/\*\*(.*?)\*\*/g, "<span class='report-bold'>$1</span>");
            
            container.innerHTML = formatted;
        })
        .catch(function(error) {
            container.innerHTML = "<span class='text-danger'>❌ Bağlantı hatası</span>";
        });
}

// Form gönderilince yapılacaklar
function formHazirla() {
    var form = document.querySelector('form');
    if (!form) return;
    
    form.addEventListener('submit', function() {
        document.getElementById('yukleniyor').style.display = 'block';
        var btn = this.querySelector('button');
        btn.classList.add('disabled');
        btn.innerHTML = '⏳ Veriler İşleniyor...';
    });
}

// Sayfa yüklenince çalışacak
document.addEventListener('DOMContentLoaded', function() {
    formHazirla();
});