import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import path from 'node:path';
import fs from 'node:fs';
const browser=await chromium.launch({channel:'chrome',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1080},deviceScaleFactor:1});
const errors=[],external=[];page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/^https?:/.test(r.url()))external.push(r.url())});
await page.goto('file://'+path.resolve('output/preview.html'));
await page.waitForFunction(()=>window.__viewer?.renderer.info.render.triangles>0);
const contract=await page.evaluate(()=>{
 const v=window.__viewer,d=v.data;return {version:d.config.version,keys:d.parts.filter(p=>p.group==='buttons').length,switches:d.parts.filter(p=>p.id.startsWith('switch_')).length,ring:!!v.objects.get('key_ring'),zeroInterference:d.report.interference_failures.length===0,oldLength:Math.max(...d.parts.find(p=>p.id==='original_top').positions.filter((_,i)=>i%3===1))-Math.min(...d.parts.find(p=>p.id==='original_top').positions.filter((_,i)=>i%3===1))};
});
assert.deepEqual(contract,{version:'0.12',keys:5,switches:8,ring:true,zeroInterference:true,oldLength:140});
assert.match(await page.locator('h1').innerText(),/0\.12/);
const imported=await page.evaluate(()=>{
 const d=window.__viewer.data,u=d.parts.find(p=>p.id==='usb_shell');
 return {usb:u.source.part,code:d.config.usb.lcsc,usbFaces:u.indices.length/3,
  colors:u.face_colors.length,oldUSB:d.parts.some(p=>p.id==='usb_tongue'),
  ordinarySwitches:d.parts.filter(p=>p.id.startsWith('switch_')&&p.source?.part==='TS-1101-C-W').length,
  centerSource:d.parts.find(p=>p.id==='switch_key_center_1').source??null,
  pins:d.report.usb.pads.map(p=>p.number).sort(),edge:d.report.usb.minimum_pad_edge_clearance,
  ledHeight:d.report.led.library_height,mountSide:d.report.usb.mount_side,microphone:d.report.microphone};
});
assert.equal(imported.usb,'HX TYPE-C 6P QTWT');assert.equal(imported.code,'C18357553');
assert.equal(imported.usbFaces,7114);assert.equal(imported.colors,7114*3);assert.equal(imported.oldUSB,false);
assert.equal(imported.ordinarySwitches,7);assert.equal(imported.centerSource,null);
assert.deepEqual(imported.pins,['17','18','19','20','A12','A5','A9','B12','B5','B9']);
assert.ok(imported.edge>.4);assert.ok(Math.abs(imported.ledHeight-1.02)<1e-6);
assert.equal(imported.mountSide,'bottom');assert.deepEqual(imported.microphone.center,[-11.25,15.45]);
const mating=await page.evaluate(()=>{
 const data=window.__viewer.data;
 return {usb:data.report.usb,latches:data.report.reference_features.usb_end_latches,holes:data.report.center_switch.locating_holes,overlaps:Object.values(data.report.interference_mm3)};
});
assert.ok(mating.overlaps.every(volume=>volume<1e-4));
assert.deepEqual(mating.usb.rotation_matrix,[[-1,0,0,0],[0,1,0,0],[0,0,-1,0],[0,0,0,1]]);
assert.equal(mating.usb.solder_plane_z,-9.05);
assert.equal(mating.usb.pad_contact_checks.length,10);
assert.ok(mating.usb.pad_contact_checks.every(pad=>pad.metal_volume_mm3>.005));
assert.ok(Object.values(mating.usb.datasheet_wider_envelope_overlap_mm3).every(volume=>volume<1e-4));
assert.equal(mating.latches.length,2);
assert.ok(mating.latches.every(latch=>latch.bottom_overlap<1e-4));
assert.ok(mating.holes.every(hole=>Math.abs(hole[0]-1)<1e-6));
await page.screenshot({path:'output/review/preview-assembled.png',fullPage:true});
await page.locator('#viewport').screenshot({path:'output/review/front-view.png'});
async function settle(){await page.waitForTimeout(280)}
async function shot(file){await settle();await page.locator('#viewport').screenshot({path:'output/review/'+file+'.png'})}
await page.locator('[data-view="end"]').click();await shot('reference-trapezoid-end');
await page.locator('[data-view="pcb"]').click();await shot('corner-notched-pcb');
const features=await page.evaluate(()=>{const v=window.__viewer;return {report:v.data.report.reference_features,visible:[...v.objects].filter(([id,m])=>m.visible).map(([id])=>id)}});
assert.equal(features.report.corner_notch_type,'concave_quarter_circle');assert.equal(features.report.width_at_former_notches,36.7574);
assert.equal(features.report.corner_fit.length,2);
for(const fit of features.report.corner_fit){assert.equal(fit.notch_radius,5);assert.equal(fit.boss_radius,4.75);assert.ok(fit.minimum_polygon_clearance>.24);assert.ok(fit.minimum_polygon_clearance<.26);assert.equal(fit.overlap_pcb,0);assert.equal(fit.overlap_top,0)}
assert.deepEqual(await page.evaluate(()=>window.__viewer.data.config.led),[-11.43,29]);assert.equal(features.report.rear_face_width,35);assert.equal(features.report.pcb_holes,5);assert.deepEqual(features.report.mounts,[[14,28],[-14,-27],[14,-27]]);assert.deepEqual(features.visible,['pcb','extension']);
await page.locator('[data-view="fit"]').click();await shot('corner-fit');
assert.equal(await page.evaluate(()=>window.__viewer.objects.get('shell_top').visible),false);
assert.equal(await page.evaluate(()=>window.__viewer.objects.get('shell_bottom').visible),true);
await page.locator('[data-group="pcb,highlight"]').uncheck();await shot('bottom-corner-locators');
assert.equal(await page.evaluate(()=>window.__viewer.objects.get('pcb').visible),false);
await page.locator('[data-group="pcb,highlight"]').check();
await page.locator('[data-view="iso"]').click();await shot('assembly-isometric');
assert.equal(await page.evaluate(()=>window.__viewer.objects.get('shell_bottom').visible),true);
await page.locator('[data-view="components"]').click();await shot('pcb-library-assembly');
assert.equal(await page.evaluate(()=>window.__viewer.objects.get('shell_top').visible),false);
assert.equal(await page.evaluate(()=>window.__viewer.objects.get('usb_shell').visible),true);
assert.equal(await page.evaluate(()=>window.__viewer.objects.get('rgb_led').visible),true);
await page.locator('[data-view="iso"]').click();
await page.locator('#explode-preset').click();await settle();assert.equal(await page.evaluate(()=>window.__viewer.getState().explode),1);await page.screenshot({path:'output/review/preview-exploded.png',fullPage:true});
await page.locator('#reset').click();await page.locator('[data-view="usb"]').click();await shot('usb-opaque');
await page.locator('#ghost').click();assert.equal(await page.evaluate(()=>window.__viewer.getState().ghost),true);await page.locator('[data-panel="usb-detail"]').click();await settle();await page.screenshot({path:'output/review/preview-usb.png',fullPage:true});
await page.locator('[data-view="usb-fit"]').click();await shot('usb-end-fit');
assert.equal(await page.evaluate(()=>window.__viewer.objects.get('shell_top').visible),false);
assert.equal(await page.evaluate(()=>window.__viewer.objects.get('shell_bottom').visible),true);
await page.locator('[data-group="pcb,highlight"]').uncheck();await shot('usb-end-sockets');
await page.locator('[data-view="usb-latches"]').click();await shot('usb-end-top-latches');
assert.equal(await page.evaluate(()=>window.__viewer.objects.get('shell_top').visible),true);
assert.equal(await page.evaluate(()=>window.__viewer.objects.get('shell_bottom').visible),false);
await page.locator('#reset').click();await page.locator('[data-view="usb"]').click();await page.locator('[data-group="shell"]').uncheck();await shot('usb-solder-face');
await page.locator('#reset').click();await page.locator('[data-view="led"]').click();await page.locator('#ghost').click();await shot('led-transparent');
await page.locator('#reset').click();await page.locator('[data-group="shell"]').uncheck();await page.locator('[data-group="buttons"]').uncheck();await settle();await page.screenshot({path:'output/review/preview-pcb.png',fullPage:true});
assert.equal(await page.evaluate(()=>window.__viewer.objects.get('shell_top').visible),false);
await page.locator('[data-view="center"]').click();await shot('center-switch-detail');
await page.locator('#reset').click();await page.locator('[data-view="center"]').click();await page.locator('#section').click();
for(const [stage,keyZ,actZ] of [[1,-.45,-.3],[2,-.7,-.55]]){
 await page.locator('[data-press="'+stage+'"]').click();await settle();
 const state=await page.evaluate(()=>({press:window.__viewer.getState().press,key:window.__viewer.objects.get('key_center').position.z,actuator:window.__viewer.objects.get('actuator_key_center_1').position.z,ring:window.__viewer.objects.get('key_ring').position.z}));
 assert.equal(state.press,stage);assert.ok(Math.abs(state.key-keyZ)<1e-8);assert.ok(Math.abs(state.actuator-actZ)<1e-8);assert.equal(state.ring,0);
 await shot('center-stage-'+stage);
}
await page.locator('#reset').click();await page.locator('[data-group="shell"]').uncheck();await page.locator('[data-group="buttons"]').uncheck();await page.locator('[data-view="back"]').click();await shot('pcb-battery-back');
await page.locator('#reset').click();await page.locator('[data-view="side"]').click();await page.locator('#section').click();await shot('center-section');assert.equal(await page.evaluate(()=>window.__viewer.getState().section),true);
await page.locator('#reset').click();await page.locator('#reference').click();await shot('original-reference');
assert.equal(await page.evaluate(()=>window.__viewer.objects.get('original_top').visible),true);
assert.equal(await page.evaluate(()=>window.__viewer.objects.get('shell_top').visible),false);
await page.locator('#reset').click();await page.locator('[data-panel="materials"]').click();await settle();await page.screenshot({path:'output/review/materials-checks.png',fullPage:true});
await page.locator('[data-panel="downloads"]').click();const dl=page.waitForEvent('download');await page.locator('[data-download="shell_top"]').click();const download=await dl;assert.equal(download.suggestedFilename(),'shell_top.stl');assert.ok(fs.statSync(await download.path()).size>100000);
await page.setViewportSize({width:390,height:844});await page.locator('#reset').click();await page.locator('[data-panel="changes"]').click();await settle();await page.screenshot({path:'output/review/preview-mobile.png',fullPage:true});
assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
assert.equal(await page.locator('#viewport canvas').count(),1);
assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
fs.writeFileSync('output/review/browser-checks.json',JSON.stringify({contract,imported_models:imported,reference_features:features.report,offline:true,no_horizontal_overflow:true,errors,external_requests:external,stl_download:true,controls:['pcb_library_assembly','source_models','usb_smt_pads','corner_fit','trapezoid_end','pcb_outline','two_stage_center_press','views','explode','ghost','section','reference','layers','reset']},null,2));
console.log('PASS: model identity, controls, original scale, offline loading, STL export, desktop/mobile layout.');
await browser.close();
