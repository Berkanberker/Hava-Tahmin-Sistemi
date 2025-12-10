using System.Diagnostics;
using Microsoft.AspNetCore.Mvc;
using ZonguldakWeb.Models;
using ZonguldakWeb.Data;
using Microsoft.EntityFrameworkCore;

namespace ZonguldakWeb.Controllers;

public class HomeController : Controller
{
    private readonly ApplicationDbContext _context;
    private readonly ILogger<HomeController> _logger;

    public HomeController(ApplicationDbContext context, ILogger<HomeController> logger)
    {
        _context = context;
        _logger = logger;
    }

    public IActionResult Index()
    {
        return View();
    }

    public async Task<IActionResult> Gecmis()
    {
        var veriler = await _context.Tahminler
            .OrderByDescending(x => x.Tarih)
            .Take(50)
            .ToListAsync();
        return View(veriler);
    }

    // --- SENİN YAZDIĞIN PROFESYONEL PYTHON ÇALIŞTIRICI ---
    private (string output, string error) RunPythonWithOutput(string scriptName, string workingDir, int timeoutSeconds = 180)
    {
        string output = "";
        string error = "";
        
        try 
        {
            // Python yolunu otomatik bulmaya çalış, bulamazsa manuel yolu kullan
            string pythonExe = @"C:\Users\TUNABERUT\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe";
            
            if (!System.IO.File.Exists(pythonExe)) 
                pythonExe = "python";

            ProcessStartInfo start = new ProcessStartInfo
            {
                FileName = pythonExe,
                // -u: Unbuffered (Anlık çıktı), -X utf8: Karakter sorunu çözücü
                Arguments = $"-u -X utf8 \"{Path.Combine(workingDir, scriptName)}\"",
                WorkingDirectory = workingDir,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true,
                StandardOutputEncoding = System.Text.Encoding.UTF8,
                StandardErrorEncoding = System.Text.Encoding.UTF8
            };

            using (Process? process = Process.Start(start))
            {
                if (process != null) 
                {
                    // Timeout kontrolü (Senin eklediğin harika özellik)
                    bool completed = process.WaitForExit(timeoutSeconds * 1000);
                    
                    if (!completed)
                    {
                        process.Kill();
                        error = $"⚠️ Script {timeoutSeconds} saniye içinde tamamlanamadı (Zaman Aşımı).";
                        _logger.LogWarning("Python Timeout: {Script}", scriptName);
                    }
                    else
                    {
                        output = process.StandardOutput.ReadToEnd();
                        error = process.StandardError.ReadToEnd();
                    }
                }
            }
        }
        catch (Exception ex)
        {
            error = $"C# Hatası: {ex.Message}";
            _logger.LogError(ex, "Python çalıştırma hatası");
        }

        return (output, error);
    }

    // --- EYLEM 1: HIZLI ANALİZ (Sayfayı Açar) ---
    [HttpPost]
    public IActionResult AnalizEt()
    {
        try 
        {
            string projeKlasoru = Directory.GetCurrentDirectory();
            
            _logger.LogInformation("Hızlı analiz (Grafik) başlatıldı...");
            
            // 1. HIZLI MOTORU ÇALIŞTIR (hava_durumu.py)
            // Bu sadece grafiği çizer ve bugünün raporunu yazar. (3-5 sn sürer)
            var sonuc = RunPythonWithOutput("hava_durumu.py", projeKlasoru, 60);
            
            // Hata varsa logla ama sayfayı patlatma
            if (!string.IsNullOrEmpty(sonuc.error)) 
                _logger.LogWarning("Hava durumu script uyarısı: {Hata}", sonuc.error);

            string raporYolu = Path.Combine(projeKlasoru, "wwwroot", "rapor.txt");
            string jsonYolu = Path.Combine(projeKlasoru, "wwwroot", "grafik_verisi.json");
            string resimBilgiDosyasi = Path.Combine(projeKlasoru, "wwwroot", "son_resim.txt");

            if (System.IO.File.Exists(raporYolu))
            {
                ViewBag.Rapor = System.IO.File.ReadAllText(raporYolu);
                
                if (System.IO.File.Exists(jsonYolu))
                    ViewBag.GrafikVerisi = System.IO.File.ReadAllText(jsonYolu);

                // Arşiv için resim yolunu al
                string arsivResmi = "/zonguldak_analiz.png";
                if (System.IO.File.Exists(resimBilgiDosyasi))
                    arsivResmi = System.IO.File.ReadAllText(resimBilgiDosyasi).Trim();

                // Veritabanına "Ön Kayıt" yap (Henüz tarihsel analiz yok)
                var yeniKayit = new HavaDurumuKayit
                {
                    Tarih = DateTime.Now,
                    RaporMetni = ViewBag.Rapor,
                    ResimYolu = arsivResmi
                };

                _context.Tahminler.Add(yeniKayit);
                _context.SaveChanges();
                
                // Bu ID'yi View'a gönderiyoruz ki JavaScript bunu kullanarak güncelleme yapabilsin
                ViewBag.KayitId = yeniKayit.Id;
                
                ViewBag.BilgiMesaji = "✅ Güncel durum analiz edildi. 🕰️ 44 Yıllık Tarihsel Tarama arka planda başlatılıyor...";
            }
            else
            {
                ViewBag.Rapor = $"🚨 HATA: Rapor dosyası oluşmadı.\nPython Çıktısı: {sonuc.output}\nPython Hatası: {sonuc.error}";
            }
        }
        catch (Exception ex)
        {
            ViewBag.Rapor = $"🚨 SİSTEM HATASI:\n{ex.Message}";
        }

        return View("Index");
    }

    // --- EYLEM 2: AĞIR ANALİZ (Arka Planda Çalışır) ---
    [HttpGet]
    public IActionResult TarihselAnalizGetir(int kayitId)
    {
        string projeKlasoru = Directory.GetCurrentDirectory();
        string dosyaYolu = Path.Combine(projeKlasoru, "wwwroot", "tarihsel_rapor.txt");
        
        // Temizlik: Eskisini sil ki yenisi gelmezse eskisiyle karışmasın
        if (System.IO.File.Exists(dosyaYolu)) System.IO.File.Delete(dosyaYolu);

        _logger.LogInformation("Tarihsel analiz (Ağır İşlem) başlatıldı...");

        // 2. AĞIR MOTORU ÇALIŞTIR (tarihsel_analiz.py)
        // Bu işlem 44 yıllık veriyi taradığı için 10-20 saniye sürebilir.
        // Timeout süresini yüksek tutuyoruz (180 sn).
        var sonuc = RunPythonWithOutput("tarihsel_analiz.py", projeKlasoru, 180);

        if (System.IO.File.Exists(dosyaYolu))
        {
            string tarihselMetin = System.IO.File.ReadAllText(dosyaYolu);
            
            // Veritabanındaki kaydı bul ve güncelle
            if (kayitId > 0)
            {
                var kayit = _context.Tahminler.Find(kayitId);
                if (kayit != null)
                {
                    // Mevcut rapora ekleme yap
                    kayit.RaporMetni += "\n\n======== 🕰️ GEÇMİŞTEN GELEN ANALİZ (SİNOPTİK) ========\n" + tarihselMetin;
                    _context.SaveChanges();
                }
            }
            
            return Content(tarihselMetin);
        }
        
        // Hata durumunda logları göster
        return Content($"🚨 Tarihsel analiz oluşturulamadı.\n\nLOGLAR:\n{sonuc.output}\n\nHATA:\n{sonuc.error}");
    }
}