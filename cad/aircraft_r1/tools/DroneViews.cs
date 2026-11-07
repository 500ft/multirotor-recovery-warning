using System;using System.IO;using System.Runtime.InteropServices;using SolidWorks.Interop.sldworks;
public class DroneViews {
 public static int Main(string[] args) {
  ISldWorks sw=(ISldWorks)Marshal.GetActiveObject("SldWorks.Application");
  if(!sw.RevisionNumber().StartsWith("34."))throw new Exception("Need 2026");
  foreach(string dir in args) {
   int e=0,w=0;string file=Path.Combine(dir,"SolidWorks",new DirectoryInfo(dir).Name+"_R1.SLDASM");
   ModelDoc2 m=(ModelDoc2)sw.OpenDoc6(file,2,1,"",ref e,ref w);if(m==null)throw new Exception("Open failed "+e);
   foreach(object o in (object[])((AssemblyDoc)m).GetComponents(false)) {
    Component2 c=(Component2)o;string n=c.Name2.ToLower();double[] rgb={.35,.38,.42};
    if(n.Contains("guard")||n.Contains("cradle"))rgb=new double[]{.93,.42,.1};
    if(n.Contains("propeller"))rgb=new double[]{.08,.65,.47};
    if(n.Contains("frame")||n.Contains("battery_pack")||n.Contains("landing"))rgb=new double[]{.18,.2,.24};
    if(n.Contains("matek")||n.Contains("mico")||n.Contains("aikon"))rgb=new double[]{.12,.42,.6};
    if(n.Contains("motor"))rgb=new double[]{.6,.63,.68};
    if(n.Contains("xt30"))rgb=new double[]{.95,.78,.1};
    c.MaterialPropertyValues=new double[]{rgb[0],rgb[1],rgb[2],.3,.8,.25,.2,0,0};
   }
   ModelView v=(ModelView)m.ActiveView;MathUtility mu=(MathUtility)sw.GetMathUtility();
   v.Orientation3=(MathTransform)mu.CreateTransform(new double[]{.7071068,-.4082483,.5773503,.7071068,.4082483,-.5773503,0,.8164966,.5773503,0,0,0,1,0,0,0});
   m.ViewZoomtofit2();m.GraphicsRedraw2();
   bool ok=m.Extension.SaveAs(Path.Combine(dir,"solidworks_isometric.png"),0,1,null,ref e,ref w);
   Console.WriteLine("VIEW "+dir+" "+ok);
   m.Save3(1,ref e,ref w);
   m.ShowNamedView2("*Front",1);m.ViewZoomtofit2();m.GraphicsRedraw2();
   m.Extension.SaveAs(Path.Combine(dir,"solidworks_top.png"),0,1,null,ref e,ref w);
   sw.CloseDoc(m.GetTitle());
  }
  return 0;
 }
}
