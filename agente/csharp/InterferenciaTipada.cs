// Verificación de interferencia con el interop TIPADO generado por GenerarInterop.exe (JRV-24). 2026-10-31.
// Nunca guarda. Solid Edge debe estar abierto.
// Se compila con compilar.py.
// Uso: InterferenciaTipada.exe <ensamble.asm> [--ignorar-roscas] [--informe ruta.txt]
using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;

static class InterferenciaTipada
{
    static string J(string s) { return "\"" + (s ?? "").Replace("\\", "\\\\").Replace("\"", "\\\"") + "\""; }

    static void Nombres(object grupo, List<string> salida)
    {
        Array arr = grupo as Array;
        if (arr == null) return;
        foreach (object o in arr)
        {
            var occ = o as SolidEdgeAssembly.Occurrence;
            if (occ != null) salida.Add(J(occ.Name));
        }
    }

    [STAThread]
    static int Main(string[] args)
    {
        try
        {
            string ruta = Path.GetFullPath(args[0]);
            bool roscas = Array.IndexOf(args, "--ignorar-roscas") >= 0;
            int k = Array.IndexOf(args, "--informe");
            object informe = k >= 0 ? (object)Path.GetFullPath(args[k + 1]) : Type.Missing;
            var app = (SolidEdgeFramework.Application)Marshal.GetActiveObject("SolidEdge.Application");
            SolidEdgeAssembly.AssemblyDocument doc = null;
            bool mio = false;
            for (int i = 1; i <= app.Documents.Count; i++)
            {
                var d = (SolidEdgeFramework.SolidEdgeDocument)app.Documents.Item(i);
                if (string.Equals(d.FullName, ruta, StringComparison.OrdinalIgnoreCase)) doc = (SolidEdgeAssembly.AssemblyDocument)d;
            }
            if (doc == null) { doc = (SolidEdgeAssembly.AssemblyDocument)app.Documents.Open(ruta); mio = true; }
            try
            {
                var occs = doc.Occurrences;
                int n = occs.Count;
                Array set1 = Array.CreateInstance(typeof(object), n);
                for (int i = 0; i < n; i++) set1.SetValue(occs.Item(i + 1), i);
                SolidEdgeAssembly.InterferenceStatusConstants status = 0;
                object num = null, ocurrencia = null, partes1 = null, partes2 = null, confirmadas = null;
                // Variantes de argumentos opcionales: la API no documenta cuáles exige (2026-10-31).
                object[][] variantes = {
                    new object[] { Type.Missing, Type.Missing, null },
                    new object[] { 0, Array.CreateInstance(typeof(object), 0), null },
                    new object[] { Type.Missing, Type.Missing, Array.CreateInstance(typeof(object), 0) },
                };
                string errores = "";
                bool hecho = false;
                foreach (var v in variantes)
                {
                    partes1 = v[2]; partes2 = v[2]; confirmadas = v[2];
                    try
                    {
                        doc.CheckInterference(n, ref set1, out status,
                            SolidEdgeConstants.InterferenceComparisonConstants.seInterferenceComparisonSet1vsItself,
                            v[0], v[1], false, informe,
                            k >= 0 ? (object)(int)(SolidEdgeConstants.InterferenceReportConstants.seInterferenceReportPartNames | SolidEdgeConstants.InterferenceReportConstants.seInterferenceReportInterferenceVolume) : Type.Missing,
                            out num, ref partes1, ref partes2, ref confirmadas, out ocurrencia, roscas);
                        hecho = true;
                        break;
                    }
                    catch (Exception e) { errores += e.Message + " | "; }
                }
                if (!hecho) throw new Exception("Ninguna variante: " + errores);
                var n1 = new List<string>(); var n2 = new List<string>();
                Nombres(partes1, n1); Nombres(partes2, n2);
                Console.WriteLine("@@RESULTADO@@ {\"ok\": true, \"codigo_estado\": " + (int)status + ", \"interferencias\": " +
                    (num == null ? "null" : num.ToString()) + ", \"ignorando_roscas\": " + (roscas ? "true" : "false") +
                    ", \"piezas_1\": [" + string.Join(", ", n1) + "], \"piezas_2\": [" + string.Join(", ", n2) + "]}");
                return 0;
            }
            finally
            {
                if (mio) doc.Close(false);
            }
        }
        catch (Exception e)
        {
            Console.WriteLine("@@RESULTADO@@ {\"ok\": false, \"error\": " + J(e.GetType().Name + ": " + e.Message) + "}");
            return 1;
        }
    }
}
