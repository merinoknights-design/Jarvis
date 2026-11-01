// Genera los ensamblados de interop TIPADOS de Solid Edge a partir de sus type libraries (como tlbimp, que no
// está instalado). Con ellos, C# puede llamar a métodos con parámetros de salida (CheckInterference, AutoExplode…)
// igual que las muestras oficiales de Siemens. 2026-10-31.
// Se compila y se ejecuta con compilar.py, que busca las type libraries del Solid Edge de este equipo.
// Uso:      GenerarInterop.exe <carpeta_salida> <Solid Edge>\Program\assembly.tlb [otras.tlb…]
using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Reflection.Emit;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;

class Sumidero : ITypeLibImporterNotifySink
{
    public void ReportEvent(ImporterEventKind kind, int code, string msg) { if (kind != ImporterEventKind.NOTIF_TYPECONVERTED) Console.WriteLine("  " + msg); }
    public Assembly ResolveRef(object typeLib) { return Programa.Convertir((ITypeLib)typeLib); }
}

static class Programa
{
    [DllImport("oleaut32.dll", CharSet = CharSet.Unicode, PreserveSig = false)]
    static extern void LoadTypeLibEx(string archivo, int regkind, out ITypeLib tl);

    static readonly Dictionary<string, Assembly> hechos = new Dictionary<string, Assembly>();

    public static Assembly Convertir(ITypeLib tl)
    {
        string nombre = Marshal.GetTypeLibName(tl);
        Assembly a;
        if (hechos.TryGetValue(nombre, out a)) return a;
        string dll = "Interop." + nombre + ".dll";
        Console.WriteLine("Convirtiendo " + nombre + " -> " + dll);
        var conv = new TypeLibConverter();
        AssemblyBuilder ab = conv.ConvertTypeLibToAssembly(tl, dll, TypeLibImporterFlags.SafeArrayAsSystemArray,
                                                           new Sumidero(), null, null, nombre, null);
        hechos[nombre] = ab;
        ab.Save(dll);
        return ab;
    }

    static int Main(string[] args)
    {
        Directory.CreateDirectory(args[0]);
        Directory.SetCurrentDirectory(args[0]);
        for (int i = 1; i < args.Length; i++)
        {
            ITypeLib tl;
            LoadTypeLibEx(args[i], 2 /* REGKIND_NONE */, out tl);
            Convertir(tl);
        }
        return 0;
    }
}
