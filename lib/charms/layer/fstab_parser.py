import re
import subprocess
from jinja2 import Environment, BaseLoader

fstab_template = """# /etc/fstab: static file system information.
#
# Use 'blkid' to print the universally unique identifier for a
# device; this may be used with UUID= as a more robust way to name devices
# that works even if disks are added and removed. See fstab(5).
#
# <file system> <mount point>   <type>  <options>       <dump>  <pass>

{% for fs in fstab %}
{{ fs['filesystem'] }} {{ fs['mountpoint'] }} {{ fs['type'] }} {{ fs['options'] }} {{ fs['dump'] }} {{ fs['pass'] }}
{% endfor %}
"""


def dict_to_fstab(fs_list, enforce=False):
    fstab = ''
    if not enforce:
        with open('/etc/fstab', 'r') as f:
            fstab = fstab_to_dict(f.readlines())
            f.close()
        for n in fs_list:
            for fs in fstab:
                if n['filesystem'] == fs['filesystem']:
                    fstab.remove(fs)
                    break
    for fs in fs_list:
        fstab.append(fs)

    for fs in fstab:
        if ('rsize' in fs) and ('wsize' in fs) and (fs['type'] == 'nfs'):
            if len(fs['options']) > 0:
                fs['options'] = 'rsize={} and wsize={},{}'.format(
                    fs['rsize'], fs['wsize'], fs['options']
                )
            else:
                fs['options'] = 'rsize={} and wsize={}'.format(
                    fs['rsize'], fs['wsize']
                )
        elif ('rsize' in fs) and (fs['type'] == 'nfs'):
            if len(fs['options']) > 0:
                fs['options'] = 'rsize={},{}'.format(
                    fs['rsize'], fs['options']
                )
            else:
                fs['options'] = 'rsize={}'.format(
                    fs['rsize']
                )
        elif ('wsize' in fs) and (fs['type'] == 'nfs'):
            if len(fs['options']) > 0:
                fs['options'] = 'wsize={},{}'.format(
                    fs['wsize'], fs['options']
                )
            else:
                fs['options'] = 'wsize={}'.format(
                    fs['wsize']
                )                
    templ = Environment(loader=BaseLoader()).from_string(fstab_template)
    fstab_content = templ.render(fstab=fstab)
    with open('/etc/fstab', 'w') as f:
        f.write(fstab_content)
        f.close()
    subprocess.check_output(['mount', '-a'])


def fstab_to_dict(fstab):
    result = []
    # Remove any lines starting with comment flag
    # clean comments from lines
    fs = [re.sub(r'\#.*$', '', i) for i in fstab if not i.startswith('#')]
    # and, remove the newline if present
    fs = [re.sub(r'(\r\n|\r|\n)', '', i) for i in fs if len(re.sub(r'(\r\n|\r|\n)', '', i))>0]
    for i in fs:  # Now we process line by line
        attrs = re.split(' |\t',i)
        # As per: https://help.ubuntu.com/community/Fstab
        # we need to account for a case where we have:
        # Server:/share  /media/nfs  nfs  rsize=8192 and wsize=8192,noexec,nosuid
        # that will break into 'rsize=8192','and','wsize=8192,noexec,nosuid'
        for j in attrs:
            if j == 'and':
                index = attrs.index(j)
                attrs[index-1] = '{},{}'.format(attrs[index-1],attrs[index+1])
                # Merged whatever existed between and
                # Now clean up since it is all in the same string
                attrs.remove(attrs[index+1])
                attrs.remove(attrs[index])
        entry = {
            'filesystem': attrs[0],
            'mountpoint': attrs[1],
            'type': attrs[2]
        }
        # NFS can carry extra params such as rsize and wsize
        # as per: https://help.ubuntu.com/community/Fstab
        # we need to account for a case where we have:
        # Server:/share  /media/nfs  nfs  rsize=8192 and wsize=8192,noexec,nosuid
        # that will break into 'rsize=8192','and','wsize=8192,noexec,nosuid'
#        for param in attrs:
#            if entry['type'] == 'nfs':
#                if 'rsize' in param:
#                    entry['rsize'] = param.split('=')[1]
#                    attrs.remove(param)
#                elif 'wsize' in param:
#                    entry['wsize'] = param.split('=')[1]
#                    attrs.remove(param)
#                elif 'and' in param:
#                    attrs.remove(param)
        if len(attrs) >= 4:
            entry['options'] = attrs[3]
        if len(attrs) >= 5:
            entry['dump'] = attrs[4]
        if len(attrs) >= 6:
            entry['pass'] = attrs[5]
        result.append(entry)
    if len(result) == 0:
        return None
    return result
