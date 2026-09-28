"""Explicit DACL export/restore; never silently changes ownership or auditing."""
import os
from pathlib import Path
from .runtime import powershell,inside


def capture(items):
    if os.name!='nt':
        return {'platform':'posix','entries':[{'path':row['relative'],'mode':Path(row['source']).stat().st_mode & 0o7777} for row in items]}
    entries=[]
    for start in range(0,len(items),100):
        values=','.join("@{source='"+row['source'].replace("'","''")+"';relative='"+row['relative'].replace("'","''")+"'}" for row in items[start:start+100])
        script="$rows=@(foreach($item in @("+values+")){try{$acl=Get-Acl -LiteralPath $item.source;@{path=$item.relative;sddl=$acl.Sddl;status='OK'}}catch{@{path=$item.relative;status='UNKNOWN'}}});ConvertTo-Json -InputObject $rows -Depth 4"
        entries.extend(powershell(script,120) or [])
    return {'platform':'windows','entries':entries,'scope':'Restore odtwarza DACL; owner/group/SACL pozostają informacją diagnostyczną.'}


def restore(root,record):
    errors=[];restored=0
    for row in record['entries']:
        target=inside(root,row['path'])
        if not target.is_file():errors.append({'path':row['path'],'error':'MISSING'});continue
        try:
            if record['platform']=='posix' and os.name!='nt':
                mode=int(row['mode'])
                if not 0<=mode<=0o7777:raise ValueError('Nieprawidłowy tryb.')
                target.chmod(mode)
            elif record['platform']=='windows' and os.name=='nt' and row.get('status')=='OK':
                path=str(target).replace("'","''");sddl=row['sddl'].replace("'","''")
                powershell("$acl=Get-Acl -LiteralPath '"+path+"';$acl.SetSecurityDescriptorSddlForm('"+sddl+"',[Security.AccessControl.AccessControlSections]::Access);Set-Acl -LiteralPath '"+path+"' -AclObject $acl;@{restored=$true}|ConvertTo-Json",30)
            else:raise ValueError('Brak zgodnych danych ACL.')
            restored+=1
        except (OSError,ValueError,RuntimeError) as exc:errors.append({'path':row['path'],'error':type(exc).__name__})
    return {'restored':restored,'errors':errors,'ok':not errors}
