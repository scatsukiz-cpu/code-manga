import sys
from PIL import Image
n=int(sys.argv[1]); ims=[Image.open(f'out/ep{n:02d}/page{i}.png') for i in range(1,5)]
s=Image.new('RGB',(1200*4+60,1600),'gray')
for i,im in enumerate(ims): s.paste(im,(i*1220,0))
s.thumbnail((2600,2600)); s.save(f'/tmp/claude-0/-home-user/89232d1c-2d1d-54b6-8849-2373ab36d573/scratchpad/v{n:02d}.png')
