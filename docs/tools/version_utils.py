import os
import subprocess


# Return the git revision as a string
def git_version(cwd):
    def _minimal_ext_cmd(cmd):
        # construct minimal environment
        env = {}
        for k in ['SYSTEMROOT', 'PATH']:
            v = os.environ.get(k)
            if v is not None:
                env[k] = v
        # LANGUAGE is used on win32
        env['LANGUAGE'] = 'C'
        env['LANG'] = 'C'
        env['LC_ALL'] = 'C'
        out = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                               env=env, cwd=cwd).communicate()[0]
        return out

    try:
        git_dir = os.path.join(cwd, ".git")
        out = _minimal_ext_cmd(['git',
                                '--git-dir',
                                git_dir,
                                'rev-parse',
                                'HEAD'])
        GIT_REVISION = out.strip().decode('ascii')[:7]

        COMMIT_COUNT = out.strip().decode('ascii')
        COMMIT_COUNT = '0' if not COMMIT_COUNT else COMMIT_COUNT
    except OSError:
        GIT_REVISION = "Unknown"
        COMMIT_COUNT = "Unknown"

    return GIT_REVISION, COMMIT_COUNT

def write_version_py(cwd):
    cnt = """\
# THIS FILE IS GENERATED DURING THE OPENTPS BUILD
# See """ + os.path.relpath(__file__, cwd) + """ for details
git_revision = '%(git_revision)s'
commit_count = '%(commit_count)s'
"""

    filename = os.path.join(cwd, "version.py")

    GIT_REVISION, COMMIT_COUNT = git_version(cwd)

    a = open(filename, 'w')
    try:
        print((GIT_REVISION, COMMIT_COUNT))
        a.write(cnt % {'git_revision': GIT_REVISION,
                       'commit_count': COMMIT_COUNT})
    finally:
        a.close()

if __name__ == "__main__":
    from opentps_core import main as mainModule

    cwd = os.path.dirname(mainModule.__file__)
    print(git_version(cwd))
    write_version_py(cwd)

