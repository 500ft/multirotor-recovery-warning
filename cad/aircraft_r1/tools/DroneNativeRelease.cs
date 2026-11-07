using System;
using System.IO;
using System.Runtime.InteropServices;
using SolidWorks.Interop.sldworks;
public class DroneNativeRelease {
  public static int Main(string[] args) {
    ISldWorks sw;
    try { sw=(ISldWorks)Marshal.GetActiveObject("SldWorks.Application"); }
    catch { sw=(ISldWorks)Activator.CreateInstance(Type.GetTypeFromProgID("SldWorks.Application.34")); }
    if(!sw.RevisionNumber().StartsWith("34.")) throw new Exception("SOLIDWORKS 2026 is required; refusing other version");
    sw.Visible=true;
    Console.WriteLine("SOLIDWORKS "+sw.RevisionNumber());
    foreach(string folder in args) {
      string native=Path.Combine(folder,"SolidWorks"); Directory.CreateDirectory(native);
      string manifest=Path.Combine(folder,"parts_to_import.txt");
      string[] steps=File.Exists(manifest)?File.ReadAllLines(manifest):Directory.GetFiles(Path.Combine(folder,"Parts_STEP"),"*.step");
      string[] natives=new string[steps.Length];
      for(int i=0;i<steps.Length;i++) {
        natives[i]=Path.Combine(native,Path.GetFileNameWithoutExtension(steps[i])+".SLDPRT");
        if(File.Exists(natives[i]))continue;
        int er=0,wa=0;
        ModelDoc2 p=(ModelDoc2)sw.LoadFile4(steps[i],"r",sw.GetImportFileData(steps[i]),ref er);
        if(p==null) throw new Exception("STEP load failed "+steps[i]+" "+er);
        natives[i]=Path.Combine(native,Path.GetFileNameWithoutExtension(steps[i])+".SLDPRT");
        if(!p.Extension.SaveAs(natives[i],0,1,null,ref er,ref wa)) throw new Exception("Part save failed "+er);
        Console.WriteLine("PART "+Path.GetFileName(natives[i])); Console.Out.Flush();
        sw.CloseDoc(p.GetTitle());
      }
      ModelDoc2 m=(ModelDoc2)sw.NewDocument(@"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2026\templates\Assembly.ASMDOT",0,0,0);
      if(m==null) throw new Exception("Assembly template failed");
      string title=m.GetTitle(); AssemblyDoc asm=(AssemblyDoc)m; MathUtility mu=(MathUtility)sw.GetMathUtility();
      foreach(string f in natives) {
        int er=0,wa=0;ModelDoc2 p=(ModelDoc2)sw.OpenDoc6(f,1,1,"",ref er,ref wa);
        sw.ActivateDoc3(title,false,0,ref er);
        Component2 c=(Component2)asm.AddComponent5(f,0,"",false,"",0,0,0);
        if(c==null) throw new Exception("AddComponent failed "+f);
        c.Transform2=(MathTransform)mu.CreateTransform(new double[]{1,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0});
        m.ClearSelection2(true);c.Select4(false,null,false);asm.FixComponent();m.ClearSelection2(true);
        sw.CloseDoc(p.GetTitle());
      }
      m.ForceRebuild3(false);m.ShowNamedView2("*Isometric",7);m.ViewZoomtofit2();
      int se=0,swa=0;string name=new DirectoryInfo(folder).Name+"_R1.SLDASM";
      if(!m.Extension.SaveAs(Path.Combine(native,name),0,1,null,ref se,ref swa))throw new Exception("Assembly save failed "+se);
      object[] comps=(object[])asm.GetComponents(false);
      Console.WriteLine("ASSEMBLY "+name+" components="+(comps==null?0:comps.Length));Console.Out.Flush();
      foreach(var view in new string[]{"Isometric","Top"}) {
        m.ShowNamedView2("*"+view,view=="Top"?5:7);m.ViewZoomtofit2();
        bool ok=m.Extension.SaveAs(Path.Combine(folder,"solidworks_"+view.ToLower()+".png"),0,1,null,ref se,ref swa);
        Console.WriteLine("VIEW "+view+" saved="+ok+" e="+se);
      }
      m.ShowNamedView2("*Isometric",7);m.ViewZoomtofit2();
      File.WriteAllText(Path.Combine(native,"native_check.txt"),"SOLIDWORKS "+sw.RevisionNumber()+"\nAssembly: "+name+"\nComponents: "+comps.Length+"\nSeparate imported-body parts, fixed at their modeled positions. Parametric source is build_drone_release.py.\n");
      sw.CloseDoc(m.GetTitle());
    }
    return 0;
  }
}
