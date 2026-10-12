using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.UI;

// Opt-in evidence only: called after a matched screenshot. Does not assign any
// font or change Text sizes, rectangles, strings, fallback lists or game rules.
public static class DSPPadFontAudit {
 [Serializable] public sealed class Glyph {public string character;public int codepoint,pixelSize,style,advance,minX,maxX,minY,maxY;public bool hasCharacter,characterInfo;public Vector2 uvBottomLeft,uvTopRight;}
 [Serializable] public sealed class Measure {public string text;public bool populated;public float width;public int characters,visible,vertices,lines;}
 [Serializable] public sealed class Sample {public string source,font,fontNames,error;public int instanceId,pixelSize;public List<Glyph> glyphs=new List<Glyph>();public List<Measure> measures=new List<Measure>();}
 [Serializable] public sealed class Report {public string label,build,system;public string[] osFontNames,osFontPaths;public List<Sample> samples=new List<Sample>();public List<string> errors=new List<string>();}
 const string Characters="0123456789尚未解锁全宇宙分钟抢先体验";
 static readonly string[] Strings={"尚未解锁","全宇宙","30/分钟","抢先体验","0123456789"};
 public static void Capture(string folder,string label){
  if(!DSPPadDiagnosticLaunch.AutomaticActionsAllowed)return;
  var report=new Report{label=label,build=DSPPadDiagnosticLaunch.BuildVersion,system=SystemInfo.operatingSystem};
  try{report.osFontNames=Font.GetOSInstalledFontNames();report.osFontPaths=Font.GetPathsToOSFonts();}catch(Exception e){report.errors.Add("OS font inventory: "+e);}
  var seen=new HashSet<string>();
  foreach(var t in UnityEngine.Object.FindObjectsOfType<Text>()){
   if(!t.isActiveAndEnabled||!t.font||t.font.name!="DIN")continue;
   int size=Mathf.RoundToInt(t.fontSize*t.pixelsPerUnit);string key=t.font.GetInstanceID()+":"+size+":"+(int)t.fontStyle;
   if(!seen.Add(key))continue;
   var settings=t.GetGenerationSettings(new Vector2(10000,10000));settings.resizeTextForBestFit=false;settings.horizontalOverflow=HorizontalWrapMode.Overflow;settings.verticalOverflow=VerticalWrapMode.Overflow;
   report.samples.Add(Probe(t.font,DSPPadRenderDiagnostics.PathOf(t.transform),size,t.fontStyle,settings));
  }
  // Loaded reference fonts are sampled without loading new project resources.
  foreach(var f in Resources.FindObjectsOfTypeAll<Font>()){
   if(f.name!="STXIHEI"&&f.name!="MEIRYO2"&&f.name!="FZXDXJW")continue;
   var settings=new TextGenerationSettings{font=f,fontSize=28,fontStyle=FontStyle.Normal,color=Color.white,scaleFactor=1,lineSpacing=1,generationExtents=new Vector2(10000,10000),horizontalOverflow=HorizontalWrapMode.Overflow,verticalOverflow=VerticalWrapMode.Overflow,richText=false};
   report.samples.Add(Probe(f,"loaded-reference",28,FontStyle.Normal,settings));
  }
  File.WriteAllText(Path.Combine(folder,label+"-font-glyphs.json"),JsonUtility.ToJson(report,true));
 }
 static Sample Probe(Font font,string source,int size,FontStyle style,TextGenerationSettings settings){
  var sample=new Sample{source=source,font=font.name,fontNames=string.Join(";",font.fontNames),instanceId=font.GetInstanceID(),pixelSize=size};
  try{
   font.RequestCharactersInTexture(Characters,size,style);
   foreach(char c in Characters){
    CharacterInfo info;bool found=font.GetCharacterInfo(c,out info,size,style);
    sample.glyphs.Add(new Glyph{character=c.ToString(),codepoint=c,pixelSize=size,style=(int)style,hasCharacter=font.HasCharacter(c),characterInfo=found,advance=info.advance,minX=info.minX,maxX=info.maxX,minY=info.minY,maxY=info.maxY,uvBottomLeft=info.uvBottomLeft,uvTopRight=info.uvTopRight});
   }
   foreach(string text in Strings)using(var generator=new TextGenerator()){
    float width=generator.GetPreferredWidth(text,settings);bool populated=generator.Populate(text,settings);
    sample.measures.Add(new Measure{text=text,width=width,populated=populated,characters=generator.characterCount,visible=generator.characterCountVisible,vertices=generator.vertexCount,lines=generator.lineCount});
   }
  }catch(Exception e){sample.error=e.ToString();}
  return sample;
 }
}
