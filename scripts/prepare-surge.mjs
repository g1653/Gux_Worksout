import { copyFileSync, readFileSync } from 'node:fs';

const domain = readFileSync(new URL('../dist/CNAME', import.meta.url), 'utf8').trim();
if (domain !== 'gux-worksout.surge.sh') throw new Error('Unexpected Surge domain');
copyFileSync(new URL('../dist/index.html', import.meta.url), new URL('../dist/200.html', import.meta.url));
console.log(`Prepared SPA fallback for https://${domain}`);
