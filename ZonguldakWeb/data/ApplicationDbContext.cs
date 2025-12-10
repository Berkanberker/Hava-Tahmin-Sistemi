using Microsoft.EntityFrameworkCore;
using ZonguldakWeb.Models;

namespace ZonguldakWeb.Data;

public class ApplicationDbContext : DbContext
{
    public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options) : base(options)
    {
    }

    public DbSet<HavaDurumuKayit> Tahminler { get; set; }
}