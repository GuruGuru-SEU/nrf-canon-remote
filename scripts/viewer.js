import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { toCreasedNormals } from 'three/addons/utils/BufferGeometryUtils.js';
const data=JSON.parse(document.getElementById('model-data').textContent);
const host=document.querySelector('#viewport');
const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,preserveDrawingBuffer:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setClearColor(0x000000,0);renderer.localClippingEnabled=true;
renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.45;
host.prepend(renderer.domElement);
const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(32,1,.1,1800);
camera.up.set(0,1,0);
const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.minDistance=15;controls.maxDistance=700;
scene.add(new THREE.HemisphereLight(0xffffff,0x697975,2.6));
for(const [pos,power,color] of [[[100,160,240],3.4,0xffffff],[[-100,-40,70],1.8,0xe0f2ff],[[50,-150,-100],2,0xffffff]]){const l=new THREE.DirectionalLight(color,power);l.position.set(...pos);scene.add(l)}
const model=new THREE.Group();scene.add(model);const objects=new Map();
function geometry(p){let g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(p.positions,3));g.setIndex(p.indices);if(p.face_colors){g=g.toNonIndexed();const colors=[],c=new THREE.Color();for(let i=0;i<p.face_colors.length;i+=3){c.setRGB(p.face_colors[i]/255,p.face_colors[i+1]/255,p.face_colors[i+2]/255,THREE.SRGBColorSpace);for(let j=0;j<3;j++)colors.push(c.r,c.g,c.b)}g.setAttribute('color',new THREE.Float32BufferAttribute(colors,3))}g.computeVertexNormals();return p.indices.length?toCreasedNormals(g,.55):g}
for(const p of data.parts){
 const g=geometry(p);
 const mat=new THREE.MeshStandardMaterial({color:p.face_colors?'#ffffff':p.color,vertexColors:!!p.face_colors,roughness:p.group==='shell'?.74:p.group==='electronics'?.43:.65,metalness:p.id==='usb_shell'?.6:p.group==='pcb'?.18:p.group==='battery'?.45:0,side:THREE.DoubleSide});
 if(p.group==='light'||p.id==='rgb_emitter'){mat.emissive=new THREE.Color('#42a995');mat.emissiveIntensity=.3}
 const mesh=new THREE.Mesh(g,mat);mesh.userData=p;mesh.fullGeometry=g;mesh.sectionGeometry=p.section?geometry(p.section):g;model.add(mesh);objects.set(p.id,mesh);
}
const groupOn={shell:true,pcb:true,electronics:true,buttons:true,switches:true,battery:true,light:true,highlight:true};
let explode=0,ghost=false,reference=false,section=false,labels=false,press=0,pcbView=false,fitView=false,componentsView=false;
const markerDefs=[{text:'01  RGB 导光柱',pos:[...data.config.led,.3],exp:26,kind:'led'},{text:'02  USB-C / 主板板舌',pos:[0,data.config.usb.front,data.report.usb.center_z],exp:0,kind:'usb'},{text:'03  '+data.config.battery.model,pos:[12.8,data.config.battery.center_xy[1],-12],exp:-10,kind:'battery'}];
for(const m of markerDefs){m.el=document.createElement('div');m.el.className='marker '+m.kind;m.el.textContent=m.text;host.append(m.el)}
function apply(){
 for(const [id,m] of objects){const p=m.userData;let visible=groupOn[p.group]??false;
 if(p.group==='reference')visible=reference&&groupOn[p.id.includes('pcb')?'pcb':p.id.startsWith('original_key')?'buttons':'shell'];
 if(reference&&['shell','pcb','buttons','light','highlight','switches','electronics','battery'].includes(p.group))visible=false;
 if(pcbView)visible=reference?id==='original_pcb':['pcb','extension'].includes(id);
 if(componentsView)visible=visible&&['pcb','highlight','electronics','switches'].includes(p.group);
 if(fitView)visible=visible&&['shell_bottom','pcb','extension','rgb_led','rgb_emitter'].includes(id);
 m.visible=visible&&(!section||m.sectionGeometry.attributes.position.count>0);m.geometry=section?m.sectionGeometry:m.fullGeometry;m.position.z=p.explode*explode*1.8;
 if(press&&!reference&&explode===0){const spec=data.config.switch_types.center;const travel=spec.travel[press-1];if(id==='key_center')m.position.z-=spec.key_gap+travel;if(id==='actuator_key_center_1')m.position.z-=travel}
 const transparent=ghost&&p.group==='shell';m.material.transparent=transparent;m.material.opacity=transparent?.18:1;m.material.depthWrite=!transparent;
 }
 document.querySelector('#state').textContent=reference?'REFERENCE / 原始模型':componentsView?'PCB ASSEMBLY / 嘉立创器件模型':pcbView?'PCB OUTLINE / 顶角 ¼ 圆凹口':fitView?'CORNER FIT / 凹口与下盖定位台':section?'SECTION / 中心剖切':explode>.1?'EXPLODED / 分解装配':'ASSEMBLY / 完整装配';
 document.querySelector('#explode-value').textContent=Math.round(explode*100)+'%';
 document.querySelector('#ghost').classList.toggle('active',ghost);document.querySelector('#section').classList.toggle('active',section);document.querySelector('#reference').classList.toggle('active',reference);
 document.querySelector('#reference-note').hidden=!reference;
 document.querySelectorAll('[data-press]').forEach(b=>b.classList.toggle('active',+b.dataset.press===press));
 document.querySelector('#press-caption').textContent=reference||explode>0?'装配状态下可预览两段按压':'K2-1831SL-A4SW-01 · '+['未按下','一段 0.30 mm · 键帽位移 0.45 mm','二段 0.55 mm · 键帽位移 0.70 mm'][press];
}
function view(which){
 pcbView=which==='pcb';fitView=which==='fit';componentsView=which==='components';if(fitView||componentsView){reference=false;ghost=false}if(pcbView||fitView||componentsView){section=false;explode=0;document.querySelector('#explode').value=0}apply();
 const distance=reference?285:185; const poses={components:[[75,-60,115],[0,0,-7.5]],fit:[[15,67,65],[0,29,-8]],iso:[[135,-70,190],[0,0,-5]],front:[[0,0,distance],[0,0,-5]],pcb:[[0,0,distance],[0,0,-5]],back:[[0,0,-distance],[0,0,-8]],usb:[[26,data.config.usb.front-42,16],[0,data.config.usb.front+6,-6]],end:[[0,data.config.usb.front-66,-8.5],[0,data.config.usb.front,-8.5]],led:[[-28,data.config.led[1]+17,43],[...data.config.led,-3]],center:[[34,16,26],[...data.config.ring_center,-4]],side:[[distance,0,0],[0,0,-7]]};
 const [p,t]=poses[which];camera.position.set(...p);controls.target.set(...t);camera.up.set(...(which==='end'?[0,0,1]:[0,1,0]));controls.update();
 document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===which));
}
for(const b of document.querySelectorAll('[data-view]'))b.onclick=()=>view(b.dataset.view);
for(const b of document.querySelectorAll('[data-press]'))b.onclick=()=>{press=+b.dataset.press;reference=false;explode=0;document.querySelector('#explode').value=0;apply()};
document.querySelector('#explode').oninput=e=>{explode=+e.target.value/100;apply()};
document.querySelector('#explode-preset').onclick=()=>{explode=explode>.1?0:1;document.querySelector('#explode').value=explode*100;apply();view('iso')};
document.querySelector('#ghost').onclick=()=>{ghost=!ghost;apply()};
document.querySelector('#section').onclick=()=>{section=!section;apply()};
document.querySelector('#reference').onclick=()=>{reference=!reference;apply();view('front')};
document.querySelector('#labels').onchange=e=>labels=e.target.checked;
for(const e of document.querySelectorAll('[data-group]'))e.onchange=()=>{for(const g of e.dataset.group.split(','))groupOn[g]=e.checked;apply()};
document.querySelector('#reset').onclick=()=>{explode=0;ghost=false;reference=false;section=false;labels=false;press=0;document.querySelector('#labels').checked=false;document.querySelector('#explode').value=0;for(const e of document.querySelectorAll('[data-group]')){e.checked=true;for(const g of e.dataset.group.split(','))groupOn[g]=true}apply();view('front')};
document.querySelector('#screenshot').onclick=()=>{renderer.render(scene,camera);const a=document.createElement('a');a.download='remote-mechanical-view.png';a.href=renderer.domElement.toDataURL();a.click()};
for(const b of document.querySelectorAll('[data-panel]'))b.onclick=()=>{document.querySelectorAll('[data-panel]').forEach(x=>x.classList.toggle('active',x===b));document.querySelectorAll('.detail-panel').forEach(x=>x.hidden=x.id!==b.dataset.panel)};
// Embedded mesh exports work from file:// without requests.
function downloadSTL(id){const p=data.parts.find(p=>p.id===id);const n=p.indices.length/3,buffer=new ArrayBuffer(84+n*50),v=new DataView(buffer);v.setUint32(80,n,true);let off=84;const a=new THREE.Vector3(),b=new THREE.Vector3(),c=new THREE.Vector3(),norm=new THREE.Vector3();for(let f=0;f<n;f++){const idx=p.indices.slice(f*3,f*3+3);a.fromArray(p.positions,idx[0]*3);b.fromArray(p.positions,idx[1]*3);c.fromArray(p.positions,idx[2]*3);norm.subVectors(b,a).cross(new THREE.Vector3().subVectors(c,a)).normalize();for(const pt of [norm,a,b,c])for(const val of pt.toArray()){v.setFloat32(off,val,true);off+=4}v.setUint16(off,0,true);off+=2}const url=URL.createObjectURL(new Blob([buffer],{type:'application/octet-stream'}));const l=document.createElement('a');l.href=url;l.download=id+'.stl';l.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
for(const b of document.querySelectorAll('[data-download]'))b.onclick=()=>downloadSTL(b.dataset.download);
new ResizeObserver(()=>{const w=host.clientWidth,h=host.clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix()}).observe(host);
const ray=new THREE.Raycaster(),mouse=new THREE.Vector2();let down=null;
renderer.domElement.addEventListener('pointerdown',e=>down=[e.clientX,e.clientY]);
renderer.domElement.addEventListener('pointerup',e=>{if(!down||Math.hypot(e.clientX-down[0],e.clientY-down[1])>4)return;const r=host.getBoundingClientRect();mouse.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1);ray.setFromCamera(mouse,camera);const hit=ray.intersectObjects([...objects.values()].filter(x=>x.visible)).find(h=>!section||h.point.x<=0);document.querySelector('#selection').textContent=hit?hit.object.userData.label:'拖动旋转 · 滚轮缩放 · 右键平移'});
function animate(){requestAnimationFrame(animate);controls.update();for(const m of markerDefs){const pt=new THREE.Vector3(...m.pos);pt.z+=m.exp*explode*1.8;pt.project(camera);const visible=labels&&!reference&&(m.kind!=='battery'||groupOn.battery&&(explode>.25||ghost||!groupOn.shell))&&(m.kind!=='led'||groupOn.light)&&(m.kind!=='usb'||groupOn.electronics)&&Math.abs(pt.x)<.94&&Math.abs(pt.y)<.94;m.el.hidden=!visible||pt.z>1;m.el.style.left=(pt.x*.5+.5)*host.clientWidth+'px';m.el.style.top=(-pt.y*.5+.5)*host.clientHeight+'px'}renderer.render(scene,camera)}
apply();view('front');animate();window.__viewer={scene,camera,objects,data,renderer,view,getState:()=>({explode,ghost,reference,section,press,pcbView,fitView})};
