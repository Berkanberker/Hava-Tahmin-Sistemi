using System.ComponentModel.DataAnnotations;

namespace ZonguldakWeb.Models;

public class HavaDurumuKayit
{
    [Key]
    public int Id { get; set; } // Kayıt Numarası

    public DateTime Tarih { get; set; } = DateTime.Now; // Ne zaman kaydedildi?
    
    public string RaporMetni { get; set; } = ""; // Yapay zeka ne dedi?
    
    public string ResimYolu { get; set; } = ""; // Grafik nerede?
}