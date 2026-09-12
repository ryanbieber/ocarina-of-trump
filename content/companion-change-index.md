# Companion change index

English companion dialogue, story mentions, HUD, all actor and message vocal triggers, title, and facing. Other language slots are preserved.

177 existing full-page WAVs plus six existing short cues. The 29 additional story/warning rewrites are text; four existing embedded cue triggers are remapped. No new full-page recordings have been made.

## Runtime fixes

| ID | Change |
|---|---|
| AUDIO-001 | 183 dedicated note layers replace out-of-range signed-8-bit jumps and shared mutable note bytes. |
| AUDIO-002 | Soundfonts 38-40 use permanent caching; audio heap grows by 64 KiB; permanent pool includes their generated sizes. WAV samples stay cartridge-backed. |
| IDENTITY-001 | Rename every quoted English Navi mention to Trump; fix companion pronouns in 0x1017 and 0x103F. |
| HUD-001 | Original TRUMP lettering in the 32x8 IA4 English C-Up label; Japanese and other language slots unchanged. |
| MODEL-001 | Follow Navi actor shape yaw after the limb matrix reset; migrate away from camera tracking. Replace the separate face shell with one welded UV-mapped head, shaped nose/jaw, and simplified matching 32x32 calm/talking textures. |
| TITLE-001 | Original 96x8 OCARINA OF TRUMP subtitle in both title draw passes. |

## Story and warning text

| Message ID | Context | Audio |
|---|---|---|
| 0x00CF | Unusable item warning | Text only |
| 0x00D0 | Locked interaction | Text only |
| 0x0228 | Point of interest | Text only |
| 0x023B | Unidentified reaction | Text only |
| 0x1000 | Trump introduces himself | Text only |
| 0x102B | Leave for Hyrule Castle | Text only |
| 0x102C | Farewell to Deku Tree | Text only |
| 0x107D | Return to Deku Tree | Text only |
| 0x1095 | Wake Link greeting | Existing short cue |
| 0x1096 | Wake Link follow-up | Existing short cue |
| 0x1098 | Urgent Deku Tree summons | Text only |
| 0x1099 | Deku Tree calls for Trump | Text only |
| 0x10B1 | Sleeping person | Text only |
| 0x3040 | Heat hazard | Text only |
| 0x305F | Shield stolen | Text only |
| 0x3060 | Tunic stolen | Text only |
| 0x3061 | Shield and tunic stolen | Text only |
| 0x3066 | Egg hatches | Text only |
| 0x401D | Underwater danger | Text only |
| 0x5071 | Sinking Shadow Temple boat | Text only |
| 0x7050 | Adult Link reveal | Text only |
| 0x7054 | Seven years later | Text only |
| 0x70CD | Ganondorf repels Trump | Existing short cue |
| 0x70D4 | After Ganondorf fight | Text only |
| 0x70D6 | Trump returns for Ganon | Existing short cue |
| 0x70E6 | Spot the legendary sword | Text only |
| 0x70E7 | Recognize legendary blade | Text only |
| 0x70E8 | Master Sword reveal | Text only |
| 0x71B0 | Timed delivery spoiled | Text only |

## English name references

0x1000, 0x1015, 0x1017, 0x102A, 0x103F, 0x1099, 0x109A

## Embedded vocal triggers

- 0x1095: NA_SE_VO_NA_HELLO_3 → generated parody cue
- 0x1096: NA_SE_VO_NA_HELLO_2 → generated parody cue
- 0x70CD: NA_SE_VO_NA_HELLO_2 → generated parody cue
- 0x70D6: NA_SE_VO_NA_HELLO_2 → generated parody cue

## Existing voiced hints and enemy advice

| Message ID | Context | WAV |
|---|---|---|
| 0x00E0 | Navi offers a Saria call | trump_00e0_00.wav |
| 0x00E1 | Navi offers her own advice | trump_00e1_00.wav |
| 0x00E2 | Navi offers to call Saria after giving advice | trump_00e2_00.wav |
| 0x00E3 | Navi offers another Saria call | trump_00e3_00.wav |
| 0x0201 | Door will not open | trump_0201_00.wav |
| 0x0202 | Iron-barred door | trump_0202_00.wav |
| 0x0203 | Small-key door | trump_0203_00.wav |
| 0x0204 | Boss-key door | trump_0204_00.wav |
| 0x020B | Puzzle-sealed entrance | trump_020b_00.wav |
| 0x0225 | Wrong-key door | trump_0225_00.wav |
| 0x0100 | Unidentified point of interest | trump_0100_00.wav |
| 0x0101 | Look below the web | trump_0101_00.wav |
| 0x0102 | Climbable vines | trump_0102_00.wav |
| 0x0103 | Opening doors | trump_0103_00.wav |
| 0x0104 | Hanging ladder | trump_0104_00.wav |
| 0x0105 | Door of Time symbol | trump_0105_00.wav |
| 0x0106 | Recently extinguished torch | trump_0106_00.wav |
| 0x0107 | Narrow-passage targeting tutorial | trump_0107_00.wav |
| 0x0108 | Movable-block tutorial | trump_0108_00.wav |
| 0x010C | Diving tutorial | trump_010c_00.wav |
| 0x0114 | Bomb Flower chain reaction | trump_0114_00.wav |
| 0x0115 | Lava-pit warning | trump_0115_00.wav |
| 0x0116 | Moving-platform switch | trump_0116_00.wav |
| 0x0119 | Blind-corner targeting reminder | trump_0119_00.wav |
| 0x011F | Look at a point of interest | trump_011f_00.wav |
| 0x0124 | Desert Colossus face | trump_0124_00.wav |
| 0x0126 | Eye of Truth clue | trump_0126_00.wav |
| 0x0128 | Sacred-feet wind clue | trump_0128_00.wav |
| 0x0129 | Danger-above warning | trump_0129_00.wav |
| 0x012A | Danger-below warning | trump_012a_00.wav |
| 0x012B | Flooding statue | trump_012b_00.wav |
| 0x012F | Green electrified tentacle | trump_012f_00.wav |
| 0x0131 | Red electrified tentacle | trump_0131_00.wav |
| 0x0132 | Blue electrified tentacle | trump_0132_00.wav |
| 0x0133 | Heavy floor switch | trump_0133_00.wav |
| 0x0137 | Tentacle-tail connection | trump_0137_00.wav |
| 0x0139 | Switch behind wall | trump_0139_00.wav |
| 0x013A | Object atop platform | trump_013a_00.wav |
| 0x013D | Real and false flags | trump_013d_00.wav |
| 0x0180 | Five Silver Rupees clue | trump_0180_00.wav |
| 0x0181 | Shadow Temple ferry clue | trump_0181_00.wav |
| 0x0183 | Unsafe shadow ferry | trump_0183_00.wav |
| 0x0184 | Door across a gap | trump_0184_00.wav |
| 0x0186 | Strange red ice | trump_0186_00.wav |
| 0x0189 | Blue Fire clue | trump_0189_00.wav |
| 0x018C | Missing Forest Temple flames | trump_018c_00.wav |
| 0x018D | Restored Forest Temple flame | trump_018d_00.wav |
| 0x018F | Arrows painted on floor | trump_018f_00.wav |
| 0x0190 | Twisted corridor | trump_0190_00.wav |
| 0x0191 | Ceiling-monster shadows | trump_0191_00.wav |
| 0x0192 | Nearby treasure chest | trump_0192_00.wav |
| 0x0194 | Forest Temple entrance torch | trump_0194_00.wav |
| 0x0195 | Lit Forest Temple torch | trump_0195_00.wav |
| 0x0197 | Frozen switch | trump_0197_00.wav |
| 0x0198 | Falling ceiling | trump_0198_00.wav |
| 0x01A3 | Goron voices below | trump_01a3_00.wav |
| 0x01A5 | Darunia room below | trump_01a5_00.wav |
| 0x01A7 | Familiar dungeon statue | trump_01a7_00.wav |
| 0x01A9 | Rusted switch | trump_01a9_00.wav |
| 0x01AB | Water vortex warning | trump_01ab_00.wav |
| 0x0140 | Great Deku Tree summons | trump_0140_00.wav |
| 0x0141 | Enter the Great Deku Tree | trump_0141_00.wav |
| 0x0142 | Visit Princess Zelda | trump_0142_00.wav |
| 0x0143 | Find Malon's father | trump_0143_00.wav |
| 0x0144 | Find Zelda in the castle | trump_0144_00.wav |
| 0x0145 | Ask Saria for guidance | trump_0145_00.wav |
| 0x0146 | Find the Fire Spiritual Stone | trump_0146_00.wav |
| 0x0147 | Enter Dodongo's Cavern | trump_0147_00.wav |
| 0x0148 | Death Mountain Great Fairy | trump_0148_00.wav |
| 0x0149 | Ask Saria about the Water Stone | trump_0149_00.wav |
| 0x014A | Princess Ruto in Jabu-Jabu | trump_014a_00.wav |
| 0x014B | Return with three Stones | trump_014b_00.wav |
| 0x014C | Object thrown into moat | trump_014c_00.wav |
| 0x014D | Check the Temple of Time | trump_014d_00.wav |
| 0x014E | Follow Sheik's Kakariko lead | trump_014e_00.wav |
| 0x0150 | Forest and Saria in danger | trump_0150_00.wav |
| 0x0151 | Death Mountain cloud | trump_0151_00.wav |
| 0x0152 | Arctic wind from Zora's River | trump_0152_00.wav |
| 0x0153 | Iron Boots diving clue | trump_0153_00.wav |
| 0x0154 | Find the remaining Sages | trump_0154_00.wav |
| 0x0155 | Monster from Kakariko well | trump_0155_00.wav |
| 0x0156 | Spirit Temple mystery | trump_0156_00.wav |
| 0x0157 | Nocturne of Shadow reminder | trump_0157_00.wav |
| 0x0158 | Search Ganondorf's desert | trump_0158_00.wav |
| 0x015A | Use the Silver Gauntlets | trump_015a_00.wav |
| 0x015B | Return to Temple of Time | trump_015b_00.wav |
| 0x015C | Rescue Zelda | trump_015c_00.wav |
| 0x015F | General progress reminder | trump_015f_00.wav |
| 0x0600 | Enemy targeting: Unknown target | trump_0600_00.wav |
| 0x0601 | Enemy targeting: Gohma | trump_0601_00.wav |
| 0x0602 | Enemy targeting: Gohma Egg | trump_0602_00.wav |
| 0x0603 | Enemy targeting: Gohma Larva | trump_0603_00.wav |
| 0x0604 | Enemy targeting: Skulltula | trump_0604_00.wav |
| 0x0605 | Enemy targeting: Big Skulltula | trump_0605_00.wav |
| 0x0606 | Enemy targeting: Tailpasaran | trump_0606_00.wav |
| 0x0607 | Enemy targeting: Deku Baba | trump_0607_00.wav |
| 0x0608 | Enemy targeting: Big Deku Baba | trump_0608_00.wav |
| 0x0609 | Enemy targeting: Withered Deku Baba | trump_0609_00.wav |
| 0x060A | Enemy targeting: Deku Scrub | trump_060a_00.wav |
| 0x060C | Enemy targeting: King Dodongo | trump_060c_00.wav |
| 0x060D | Enemy targeting: Dodongo | trump_060d_00.wav |
| 0x060E | Enemy targeting: Baby Dodongo | trump_060e_00.wav |
| 0x060F | Enemy targeting: Lizalfos | trump_060f_00.wav |
| 0x0610 | Enemy targeting: Dinolfos | trump_0610_00.wav |
| 0x0611 | Enemy targeting: Fire Keese | trump_0611_00.wav |
| 0x0612 | Enemy targeting: Keese | trump_0612_00.wav |
| 0x0613 | Enemy targeting: Armos | trump_0613_00.wav |
| 0x0614 | Enemy targeting: Barinade | trump_0614_00.wav |
| 0x0615 | Enemy targeting: Parasitic Tentacle | trump_0615_00.wav |
| 0x0616 | Enemy targeting: Shabom | trump_0616_00.wav |
| 0x0617 | Enemy targeting: Biri | trump_0617_00.wav |
| 0x0618 | Enemy targeting: Bari | trump_0618_00.wav |
| 0x0619 | Enemy targeting: Stinger | trump_0619_00.wav |
| 0x061A | Enemy targeting: Phantom Ganon, mounted | trump_061a_00.wav |
| 0x061B | Enemy targeting: Stalfos | trump_061b_00.wav |
| 0x061C | Enemy targeting: Blue Bubble | trump_061c_00.wav |
| 0x061D | Enemy targeting: White Bubble | trump_061d_00.wav |
| 0x061E | Enemy targeting: Green Bubble | trump_061e_00.wav |
| 0x061F | Enemy targeting: Skullwalltula | trump_061f_00.wav |
| 0x0620 | Enemy targeting: Gold Skulltula | trump_0620_00.wav |
| 0x0621 | Enemy targeting: Volvagia | trump_0621_00.wav |
| 0x0622 | Enemy targeting: Flare Dancer | trump_0622_00.wav |
| 0x0623 | Enemy targeting: Torch Slug | trump_0623_00.wav |
| 0x0624 | Enemy targeting: Red Bubble | trump_0624_00.wav |
| 0x0625 | Enemy targeting: Morpha | trump_0625_00.wav |
| 0x0626 | Enemy targeting: Dark Link | trump_0626_00.wav |
| 0x0627 | Enemy targeting: Shell Blade | trump_0627_00.wav |
| 0x0628 | Enemy targeting: Spike | trump_0628_00.wav |
| 0x0629 | Enemy targeting: Bongo Bongo | trump_0629_00.wav |
| 0x062A | Enemy targeting: Redead | trump_062a_00.wav |
| 0x062B | Enemy targeting: Phantom Ganon | trump_062b_00.wav |
| 0x062D | Enemy targeting: Gibdo | trump_062d_00.wav |
| 0x062E | Enemy targeting: Dead Hand's hand | trump_062e_00.wav |
| 0x062F | Enemy targeting: Dead Hand | trump_062f_00.wav |
| 0x0630 | Enemy targeting: Wallmaster | trump_0630_00.wav |
| 0x0631 | Enemy targeting: Floormaster | trump_0631_00.wav |
| 0x0632 | Enemy targeting: Koume | trump_0632_00.wav |
| 0x0633 | Enemy targeting: Kotake | trump_0633_00.wav |
| 0x0634 | Enemy targeting: Nabooru Iron Knuckle | trump_0634_00.wav |
| 0x0635 | Enemy targeting: Iron Knuckle | trump_0635_00.wav |
| 0x0636 | Enemy targeting: Adult Skull Kid | trump_0636_00.wav |
| 0x0637 | Enemy targeting: Like Like | trump_0637_00.wav |
| 0x0639 | Enemy targeting: Beamos | trump_0639_00.wav |
| 0x063A | Enemy targeting: Anubis | trump_063a_00.wav |
| 0x063B | Enemy targeting: Freezard | trump_063b_00.wav |
| 0x063D | Enemy targeting: Ganondorf | trump_063d_00.wav |
| 0x063E | Enemy targeting: Ganon | trump_063e_00.wav |
| 0x063F | Enemy targeting: Skull Kid | trump_063f_00.wav |
| 0x0640 | Enemy targeting: Friendly Skull Kid | trump_0640_00.wav |
| 0x0641 | Enemy targeting: Masked Skull Kid | trump_0641_00.wav |
| 0x0642 | Enemy targeting: Octorok | trump_0642_00.wav |
| 0x0643 | Enemy targeting: Composer Poe | trump_0643_00.wav |
| 0x0644 | Enemy targeting: Poe | trump_0644_00.wav |
| 0x0645 | Enemy targeting: Red Tektite | trump_0645_00.wav |
| 0x0646 | Enemy targeting: Blue Tektite | trump_0646_00.wav |
| 0x0647 | Enemy targeting: Leever | trump_0647_00.wav |
| 0x0648 | Enemy targeting: Peahat | trump_0648_00.wav |
| 0x0649 | Enemy targeting: Peahat Larva | trump_0649_00.wav |
| 0x064A | Enemy targeting: Moblin | trump_064a_00.wav |
| 0x064B | Enemy targeting: Club Moblin | trump_064b_00.wav |
| 0x064C | Enemy targeting: Wolfos | trump_064c_00.wav |
| 0x064D | Enemy targeting: Mad Scrub | trump_064d_00.wav |
| 0x064E | Enemy targeting: Business Scrub | trump_064e_00.wav |
| 0x064F | Enemy targeting: Dampe's Ghost | trump_064f_00.wav |
| 0x0650 | Enemy targeting: Poe Sister Meg | trump_0650_00.wav |
| 0x0651 | Enemy targeting: Poe Sister Joelle | trump_0651_00.wav |
| 0x0652 | Enemy targeting: Poe Sister Beth | trump_0652_00.wav |
| 0x0653 | Enemy targeting: Poe Sister Amy | trump_0653_00.wav |
| 0x0654 | Enemy targeting: Gerudo Thief | trump_0654_00.wav |
| 0x0655 | Enemy targeting: Stalchild | trump_0655_00.wav |
| 0x0656 | Enemy targeting: Ice Keese | trump_0656_00.wav |
| 0x0657 | Enemy targeting: White Wolfos | trump_0657_00.wav |
| 0x0658 | Enemy targeting: Guay | trump_0658_00.wav |
| 0x0659 | Enemy targeting: Bigocto | trump_0659_00.wav |
| 0x065A | Enemy targeting: Big Poe | trump_065a_00.wav |
| 0x065B | Enemy targeting: Twinrova | trump_065b_00.wav |
| 0x065C | Enemy targeting: Wasteland Poe | trump_065c_00.wav |

## Runtime acceptance

Pending user cold-boot replay of intro and normal speech; builds and static checks do not prove runtime acceptance.
