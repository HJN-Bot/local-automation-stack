#!/usr/bin/env node
import fs from 'node:fs';
const src=process.argv[2];
if(!src){ console.error('Usage: node restore-prompts-from-backup.mjs <backup.json>'); process.exit(1); }
const dst='/home/ubuntu/.openclaw/openclaw.json';
const S=JSON.parse(fs.readFileSync(src,'utf8'));
const D=JSON.parse(fs.readFileSync(dst,'utf8'));
const ids=['1472614324009697412','1472614337016238303','1472614358466170930','1472614370260287561'];
const sc=S.channels.discord.guilds['1467170598529794317'].channels;
const dc=D.channels.discord.guilds['1467170598529794317'].channels;
for(const cid of ids){
  if(sc[cid]?.systemPrompt){ dc[cid] ??= {}; dc[cid].systemPrompt=sc[cid].systemPrompt; dc[cid].allow=true; dc[cid].requireMention=false; }
}
fs.writeFileSync(dst,JSON.stringify(D,null,2));
console.log('restored prompts to',dst);
