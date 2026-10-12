"""Install previously staged platform hooks from the owner's private source.

No recovered methods are distributed. Existing game calculations, clipboard
validation on explicit Paste, and keyboard camera bindings remain unchanged.
"""
import argparse,re
from pathlib import Path
from apply_managed_input_trace import patch as trace_input

def after(text,anchor,call):
    hook='\n#if DSP_EMU_IPAD\n'+call+'\n#endif'
    if hook in text:return text
    if text.count(anchor)!=1:raise ValueError('Unsupported hook: '+anchor)
    return text.replace(anchor,anchor+hook,1)

def clipboard(text):
    # UIKit pasteboard reads at window-open otherwise prompt before the user
    # chooses Paste. Original Paste handlers still perform full validation.
    pattern=r'(?m)^(\s*)(bpPasteButton\d*\.button\.interactable) = editor\.blueprint\.CheckValid\(GUIUtility\.systemCopyBuffer, EDysonBlueprintType\.\w+\);$'
    if 'Validate on the original explicit Paste action.' in text:return text
    def replace(m):
        indent=m[1].lstrip('\n')
        return '#if DSP_EMU_IPAD\n'+indent+m[2]+' = true; // Validate on the original explicit Paste action.\n#else\n'+m[0]+'\n#endif'
    updated,count=re.subn(pattern,replace,text)
    if count not in (1,2):raise ValueError('Expected original Dyson Paste availability checks')
    return updated

def apply(project):
    game=Path(project)/'Assets/Scripts/Assembly-CSharp'
    def edit(name,fn):
        p=game/name;p.write_text(fn(p.read_text()))
    for name in ['UIDELayerPanel.cs','UIDESwarmPanel.cs','UIDEOverview.cs']:edit(name,clipboard)
    def hierarchy(s):
        anchor='\tpublic void CheckCopyBoard()\n\t{'
        marker='// iPad: read pasteboard only from explicit Paste handlers.'
        if marker in s:return s
        start=s.index(anchor)+len(anchor);end=s.index('\n\t}',start)
        controls=['hierarchy.layerPanel.bpPasteButton1','hierarchy.layerPanel.bpPasteButton2','hierarchy.swarmPanel.bpPasteButton','inspector.overview.bpPasteButton']
        body='\n#if DSP_EMU_IPAD\n        '+marker+'\n'+''.join('        controlPanel.'+c+'.button.interactable=true;\n' for c in controls)+'        return;\n#else'
        return s[:start]+body+s[start:end]+'\n#endif'+s[end:]
    edit('UIDysonEditor.cs',hierarchy)
    edit('VFInput.cs',trace_input)
    edit('PlayerController.cs',lambda s:after(s,'\t\tGetInput();','\t\tDSPPadManagedInputTrace.AfterControllerInput();'))
    # These legacy touch transport hooks are dormant in the keyboard bundle.
    edit('PlayerController.cs',lambda s:after(s,'\t\t\tinput0.Normalize();','\t\t\tif (DSPSmartTouchFrame.Enabled && DSPSmartTouchFrame.Move.sqrMagnitude > 0f) { input0.x=DSPSmartTouchFrame.Move.x; input0.y=DSPSmartTouchFrame.Move.y; }'))
    for name in ['ThirdPersonPoser','PlanetPoser','SailPoser','RTSPoser','GraticulePoser']:
        def look(s):
            old='VFInput._cameraRTSRotateButton.pressing';new='('+old+' || DSPSmartTouchFrame.LookHeld)'
            if new in s:return s
            if s.count(old)!=1:raise ValueError('Unknown camera input consumer')
            return s.replace(old,new,1)
        edit(name+'.cs',look)
    edit('DSPGame.cs',lambda s:after(s,'\t\tLocalization.OnLanguageChange += OnLanguageChange;\n\t\tOnLanguageChange();','\t\tDSPPadMemoryPressureProbe.AfterStartup();'))
    # Memory probe is opt-in and runs before the original menu demo starts.
    p=game/'VFPreload.cs';s=p.read_text();hook='#if DSP_EMU_IPAD\n\t\tDSPPadMemoryPressureProbe.BeforeMenuDemo();\n#endif\n'
    if hook not in s:
        anchor='\t\tDSPGame.StartDemoGame(num21);'
        if s.count(anchor)!=1:raise ValueError('Unknown menu demo boundary')
        p.write_text(s.replace(anchor,hook+anchor,1))
    plans=[('BloomComponent.cs','\t\t\tGraphics.Blit(source, renderTexture, material, 0);','bloom-prefilter','renderTexture'),
           ('DepthOfFieldComponent.cs','\t\t\tRenderTextureFormat format = RenderTextureFormat.DefaultHDR;','dof-source','source'),
           ('DepthOfFieldComponent.cs','\t\t\tcocRtex = renderTexture;','dof-coc','renderTexture'),
           ('DepthOfFieldComponent.cs','\t\t\tGraphics.Blit(source, renderTexture2, material, 2);','dof-prefilter','renderTexture2'),
           ('DepthOfFieldComponent.cs','\t\t\tGraphics.Blit(renderTexture2, renderTexture3, material, (int)(3 + settings.kernelSize));','dof-bokeh','renderTexture3'),
           ('DepthOfFieldComponent.cs','\t\t\tGraphics.Blit(renderTexture3, renderTexture2, material, 7);','dof-postfilter','renderTexture2'),
           ('PostProcessingBehaviour.cs','\t\tprivate void OnRenderImage(RenderTexture source, RenderTexture destination)\n\t\t{','post-source-" + name + "','source')]
    for name,anchor,label,value in plans:
        expression='"post-source-" + name' if name=='PostProcessingBehaviour.cs' else '"'+label+'"'
        edit('UnityEngine/PostProcessing/'+name,lambda s:after(s,anchor,'            DSPPadRenderFormats.Note('+expression+', '+value+');'))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',type=Path,required=True);apply(p.parse_args().project)
