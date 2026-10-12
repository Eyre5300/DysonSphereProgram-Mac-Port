#!/usr/bin/env python3
"""Apply only the UIKit transport hook to a generated Unity trampoline copy."""
import argparse, hashlib, json, plistlib, re
from pathlib import Path

DECL='extern "C" NSSet<UITouch*> *DSPPortFilterPointerTouches(NSSet<UITouch*> *touches, UIEvent *event, UIView *view);'
KINDS={'Began':'Begin','Ended':'Ended','Cancelled':'Cancelled','Moved':'Moved'}
def transform_view(source):
    if DECL in source:
        for kind,call in KINDS.items():
            assert f'if(fingers.count) UnitySendTouches{call}(fingers, event);' in source
        return source,False
    anchor='#import "UnityView.h"'
    if source.count(anchor)!=1:
        raise ValueError('Expected one UnityView.h import in the generated iOS trampoline.')
    result=source.replace(anchor,anchor+'\n'+DECL,1)
    for kind,call in KINDS.items():
        pattern=rf'- \(void\)touches{kind}:\(NSSet\*\)touches withEvent:\(UIEvent\*\)event\s*\{{ UnitySendTouches{call}\(touches, event\); \}}'
        result,count=re.subn(pattern, f'- (void)touches{kind}:(NSSet*)touches withEvent:(UIEvent*)event {{ NSSet *fingers=DSPPortFilterPointerTouches(touches,event,self); if(fingers.count) UnitySendTouches{call}(fingers, event); }}',result)
        if count!=1:
            raise ValueError(f'Expected exactly one original touches{kind} forwarding method; found {count}.')
    return result,True

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--view',type=Path,required=True)
    parser.add_argument('--plist',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    original=args.view.read_text();updated,changed=transform_view(original)
    plist_original=args.plist.read_bytes();info=plistlib.loads(plist_original);before=dict(info)
    info['UIApplicationSupportsIndirectInputEvents']=True
    assert {k:v for k,v in info.items() if k!='UIApplicationSupportsIndirectInputEvents'}=={k:v for k,v in before.items() if k!='UIApplicationSupportsIndirectInputEvents'}
    if changed:args.view.write_text(updated)
    if before.get('UIApplicationSupportsIndirectInputEvents') is not True:
        # The generated engine project plist is XML. The app build copies this key.
        args.plist.write_bytes(plistlib.dumps(info,fmt=plistlib.FMT_XML,sort_keys=False))
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps({'view':str(args.view),'plist':str(args.plist),'viewChanged':changed,'beforeSupportsIndirectInputEvents':before.get('UIApplicationSupportsIndirectInputEvents'),'supportsIndirectInputEvents':info['UIApplicationSupportsIndirectInputEvents'],'viewBeforeSHA256':hashlib.sha256(original.encode()).hexdigest(),'viewAfterSHA256':hashlib.sha256(updated.encode()).hexdigest(),'filteredTouchType':'UITouchTypeIndirectPointer only','otherPlistValuesUnchanged':True},indent=2))
if __name__=='__main__':main()
