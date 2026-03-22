#!/usr/bin/env node
import fs from 'node:fs';
const cfg=process.env.OPENCLAW_CONFIG || '/home/ubuntu/.openclaw/openclaw.json';
const bak=`${cfg}.bak-${new Date().toISOString().replace(/[:.]/g,'-')}`;
fs.copyFileSync(cfg,bak);
const j=JSON.parse(fs.readFileSync(cfg,'utf8'));
j.channels ??= {}; j.channels.discord ??= {}; j.channels.discord.groupPolicy='allowlist';
const g=j.channels.discord?.guilds?.['1467170598529794317']?.channels || {};
for (const cid of ['1472614324009697412','1472614337016238303','1472614358466170930','1472614370260287561','1476944737931100221']){
  g[cid] ??= {}; g[cid].allow=true; g[cid].requireMention=false;
}
if (j.channels.discord?.guilds?.['1467170598529794317']) j.channels.discord.guilds['1467170598529794317'].channels=g;
fs.writeFileSync(cfg,JSON.stringify(j,null,2));
console.log('backup:',bak);
console.log('hardened:',cfg);
