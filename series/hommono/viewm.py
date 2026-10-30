import sys
from PIL import Image
eps=[int(a) for a in sys.argv[1:]]; W=300; H=400
s=Image.new('RGB',(W*4+30,len(eps)*(H+10)),'gray')
for r,n in enumerate(eps):
    for i in range(4):
        im=Image.open(f'out/ep{n:02d}/page{i+1}.png').resize((W,H)); s.paste(im,(i*(W+10),r*(H+10)))
s.save('/tmp/claude-0/-home-user/89232d1c-2d1d-54b6-8849-2373ab36d573/scratchpad/vm.png')
