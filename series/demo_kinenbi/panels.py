import subprocess,sys,json
S="Black and white Japanese josei manga panel, clean professional ink line art, screentone shading, cinematic composition. Single panel illustration, no panel borders, no text, no speech bubbles, no sound effects. "
L="Lin Xia (the woman in the reference sheet: long straight black hair half-up with a pearl hair clip, navy dress, pendant necklace, wedding ring)"
J="Lu Jingshen (the man in the reference sheet: swept-back black hair, cold sharp eyes, dark three-piece suit)"
W="Su Wan (the woman in the reference sheet: wavy shoulder-length light brown hair, white off-shoulder dress)"
P={
"p1_1":("1536x1024",[], "Night. Wide establishing shot inside a luxurious high-floor restaurant: floor-to-ceiling windows with a glittering Shanghai-like city skyline and river, crystal chandeliers. In the foreground a single window table set for two, with candles, roses, wine glasses and a small wrapped gift box. No people visible."),
"p1_2":("1536x1024",["chars/linxia.png"], f"{L} sits alone at the window table in the luxury restaurant at night, back straight, smiling hopefully and glancing toward the restaurant entrance. The chair across from her is empty. A small gift box on the table. Medium shot."),
"p1_3":("1024x1536",["chars/linxia.png"], f"Close-up: {L}'s hand (wedding ring visible) holding a smartphone to make a call that nobody answers; the screen shows a calling screen with a blank avatar. Beside it, candles burned down to stubs with melted wax. In the background a wall clock pointing near 11 o'clock."),
"p1_4":("1536x1024",["chars/linxia.png"], f"The luxury restaurant is now almost empty and dim. In the background a waiter stacks chairs onto tables. {L} sits alone at the window table, head lowered, eyes downcast, the untouched cold food and unopened gift box in front of her. Lonely, heartbreaking mood."),
"p2_1":("1536x1024",[], "Close-up on a dark restaurant tabletop at night: a smartphone lying face up suddenly lights up with a notification glow and vibrates, small vibration lines around it. A woman's hand with a thin gold wedding ring reaches toward it. Burned-out candles nearby."),
"p2_2":("1024x1024",["chars/jingshen.png","chars/suwan.png"], f"A casual smartphone selfie photo at a private birthday party: {W} holds the camera, leaning happily on the shoulder of {J}, who is smiling softly and gently at her (a warm expression he never shows his wife). In front of them a birthday cake with lit candles. Cozy, warm, intimate atmosphere, balloons in the background."),
"p2_3":("1536x1024",["chars/linxia.png"], f"Extreme close-up of {L}'s face lit by the cold glow of a phone screen: her smile is slowly collapsing, eyes empty and wide, the light fading from her pupils, a single tear about to fall. Dark background, dramatic shadows."),
"p3_1":("1536x1024",["chars/linxia.png","chars/jingshen.png"], f"Flashback, soft dreamy light and sparkles: a wedding ceremony. {J} in a black tuxedo gently slides a wedding ring onto the finger of {L} in a white wedding dress and veil; both smiling, he looks at her tenderly. Soft focus, flower petals."),
"p3_2":("1024x1024",["chars/linxia.png"], f"Extreme close-up of {L}'s hands: she slowly slides the thin gold wedding ring off her ring finger. A tear drop falls onto the back of her hand. Dark background."),
"p3_3":("1536x1024",["chars/linxia.png"], f"Late night in a large, cold, modern luxury apartment. {L} sits alone at a dining table under a single pendant lamp, signing a document with a pen. The document's title is clearly written in Japanese kanji: 離婚協議書. Her expression is calm and resolved, eyes red from crying. The wedding ring lies beside the paper."),
"p3_4":("1536x1024",["chars/linxia.png"], f"Dawn. {L}, now in a simple coat, stands at the open front door of the luxury apartment with a single suitcase, seen from behind, pale morning light flooding in from outside. She does not look back. Quiet, resolute, liberating mood."),
"p4_1":("1536x1024",["chars/jingshen.png"], f"Morning. {J} walks into the spacious modern living room of his apartment, loosening his tie with one hand and holding his phone in the other, with an indifferent, slightly impatient expression, about to call out to his wife. Bright morning light."),
"p4_2":("1536x1024",[], "Top-down view of a dining table in a luxury apartment in the morning light: a signed document titled in Japanese kanji 離婚協議書, a thin gold wedding ring placed on top of it, a house key beside it, and a small unopened wrapped gift box. Nothing else. Quiet, cold mood."),
"p4_3":("1536x1024",["chars/jingshen.png"], f"Dramatic close-up of {J} gripping a document in his trembling hand, face frozen in shock: eyes wide with shrunken pupils, cold sweat, mouth slightly open, his perfect composure shattered. Manga shock vertical lines over his face, dark radiating speed lines in the background."),
}
keys=sys.argv[1:] or list(P)
procs=[]
for k in keys:
    size,refs,pr=P[k]
    procs.append(subprocess.Popen(["python3","gen2.py",f"panels/{k}.png",size,S+pr,*refs]))
    if len(procs)>=5:
        [p.wait() for p in procs]; procs=[]
[p.wait() for p in procs]
