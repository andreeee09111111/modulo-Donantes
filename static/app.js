'use strict';
const $ = id => document.getElementById(id);
const state = {token:null, user:null, donations:[], organizations:[], donors:[], accounts:[], generation:0, profileId:null, organizationId:null, statusChange:null};
const labels = {pendiente:'Pendiente',aprobada:'Aprobada',en_camino:'En camino',entregada:'Entregada',rechazada:'Rechazada',cancelada:'Cancelada'};
const categoryLabels = {alimentos:'Alimentos',ropa:'Ropa',higiene:'Higiene',utiles:'Útiles escolares',otros:'Otros'};
const symbols = {alimentos:'♧',ropa:'♧',higiene:'◇',utiles:'▤',otros:'□'};
const actionLabels = {aprobada:'Aprobar donación',en_camino:'Marcar en camino',entregada:'Confirmar entrega',rechazada:'Rechazar donación',cancelada:'Cancelar donación'};
const admin = () => state.user?.rol === 'administrador';
const myProfile = () => state.donors.find(row => row.usuario_id === state.user?.id);
function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined && text !== null) element.textContent = text;
  if (className) element.className = className;
  return element;
}
let noticeTimer;
function notify(text) {
  clearTimeout(noticeTimer); $('notice').textContent = text; $('notice').hidden = !text;
  noticeTimer = setTimeout(() => { $('notice').hidden = true; }, 6500);
}
function logout() {
  state.generation++; state.token = null; state.user = null;
  state.donations = []; state.donors = []; state.organizations = []; state.accounts = [];
  document.querySelectorAll('dialog[open]').forEach(dialog => dialog.close());
  document.querySelectorAll('form').forEach(form => form.reset());
  $('application').hidden = true; $('login-view').hidden = false;
  $('login-error').textContent = ''; $('notice').hidden = true;
  $('donation-search').value = ''; $('state-filter').value = '';
  for (const id of ['recent-list','donation-list','organizations','profile-card','donor-list','detail-content']) $(id).replaceChildren();
}
async function api(path, options = {}) {
  const generation = state.generation;
  const response = await fetch(path, {...options, headers:{'Content-Type':'application/json', ...(state.token ? {Authorization:`Bearer ${state.token}`} : {})}});
  const data = response.status === 204 ? null : await response.json();
  if (generation !== state.generation) throw new Error('La sesión cambió. Vuelve a intentar.');
  if (!response.ok) {
    if (response.status === 401 && state.token) logout();
    throw new Error(data?.error || `Error ${response.status}`);
  }
  return data;
}
function button(text, action, className = 'secondary') {
  const element = node('button', text, className); element.type = 'button';
  element.addEventListener('click', async () => {
    element.disabled = true;
    try { await action(); } catch (error) { notify(error.message); }
    finally { element.disabled = false; }
  });
  return element;
}
function empty(title, description, label, action) {
  const box = node('div', null, 'empty');
  box.append(node('div','♡','empty-symbol'), node('h3',title), node('p',description));
  if (label) box.append(button(label,action,'primary'));
  return box;
}
function field(label, value, className = '') {
  const item = node('div',null,className);
  item.append(node('span',label,'field-label'),node('div',value || 'Sin indicaciones adicionales','field-value'));
  return item;
}
function pill(status) { return node('span', labels[status] || status, `pill ${status}`); }
function dateText(value, time = false) {
  return new Date(value.length === 10 ? `${value}T12:00:00` : value).toLocaleString('es-MX', {day:'numeric',month:'short',year:'numeric',...(time ? {hour:'2-digit',minute:'2-digit'} : {})});
}
function navigate(page) {
  if (page === 'donors' && !admin()) return;
  for (const section of document.querySelectorAll('.page')) section.hidden = section.id !== `page-${page}`;
  for (const link of document.querySelectorAll('.nav')) {
    const active = link.dataset.page === page;
    link.classList.toggle('active',active);
    if (active) link.setAttribute('aria-current','page'); else link.removeAttribute('aria-current');
  }
  const names = {home:'Resumen',donations:admin()?'Todas las donaciones':'Mis donaciones',destinations:'Destinos',profile:'Mi perfil',donors:'Donantes'};
  $('breadcrumb').textContent = `Mi espacio / ${names[page]}`;
  window.scrollTo({top:0,behavior:'instant'});
}
function openDialog(id) {
  const dialog = $(id);
  dialog.querySelectorAll('.form-error').forEach(error => { error.textContent = ''; });
  if (!dialog.open) dialog.showModal();
}
function fillSelect(id, rows, title) {
  $(id).replaceChildren();
  for (const row of rows) {
    const option = node('option',title(row)); option.value = row.id; $(id).append(option);
  }
}
async function refresh() {
  const generation = state.generation;
  const requests = ['/api/donaciones','/api/organizaciones','/api/donantes'];
  if (admin()) requests.push('/api/usuarios');
  const [donations,organizations,donors,accounts] = await Promise.all(requests.map(path => api(path)));
  if (!state.user || generation !== state.generation) return;
  Object.assign(state,{donations,organizations,donors,accounts:accounts || []});
  render();
}
function donationRow(donation, full = false) {
  const row = node('article',null,`donation-row${full ? ' donation-full' : ''}`);
  row.append(node('div',symbols[donation.categoria] || '□','donation-symbol'));
  const information = node('div',null,'donation-info');
  information.append(node('h3',donation.titulo),node('p',`${donation.cantidad} ${donation.unidad} · ${donation.destino_nombre}`));
  if (full) {
    information.append(node('p',`${donation.folio} · Fecha propuesta: ${dateText(donation.fecha_prevista)}`));
    if (admin()) information.append(node('p',`Donante: ${donation.donante_nombre}`));
  }
  const end = node('div',null,'donation-end');
  end.append(pill(donation.estado),button('Ver seguimiento →',() => showDetail(donation.id),'text-button'));
  row.append(information,end); return row;
}
function renderHistory() {
  const query = $('donation-search').value.toLocaleLowerCase().trim();
  const status = $('state-filter').value;
  const list = state.donations.filter(row => (!status || status === row.estado) && `${row.titulo} ${row.folio} ${row.destino_nombre} ${row.donante_nombre}`.toLocaleLowerCase().includes(query));
  $('results-count').textContent = `${list.length} de ${state.donations.length} donaciones`;
  $('donation-list').replaceChildren(...list.map(row => donationRow(row,true)));
  if (!list.length) $('donation-list').append(empty(state.donations.length ? 'No hay coincidencias' : 'Tu primera donación empieza aquí',state.donations.length ? 'Prueba con otro texto o cambia el filtro de estado.' : 'Registra lo que quieres compartir y elige a qué organización llegará.',state.donations.length ? null : 'Registrar mi primera donación',() => newDonation()));
}
function renderHome() {
  const donations = state.donations;
  const values = [
    ['Donaciones registradas',donations.length,'Todo tu historial','♡'],
    ['En proceso',donations.filter(d=>['pendiente','aprobada','en_camino'].includes(d.estado)).length,'Pendientes de entrega','◷'],
    ['Entregadas',donations.filter(d=>d.estado === 'entregada').length,'Entrega confirmada','✓'],
    ['Destinos elegidos',new Set(donations.filter(d=>!['rechazada','cancelada'].includes(d.estado)).map(d=>d.organizacion_id)).size,'Organizaciones beneficiarias','⌖']
  ];
  $('metrics').replaceChildren();
  for (const [label,total,description,icon] of values) {
    const card = node('article',null,'metric'), top = node('div',null,'metric-top');
    top.append(node('span',label),node('span',icon,'metric-icon'));
    card.append(top,node('strong',total),node('small',description)); $('metrics').append(card);
  }
  const recent = [...donations].sort((a,b)=>b.actualizado.localeCompare(a.actualizado)).slice(0,4);
  $('recent-list').replaceChildren(...recent.map(row=>donationRow(row)));
  if (!recent.length) $('recent-list').append(empty('Aún no hay donaciones','Cuando registres un aporte, verás aquí su destino y seguimiento.','Nueva donación',()=>newDonation()));
  const active = state.organizations.filter(row => row.activo);
  $('destination-summary').replaceChildren(...active.slice(0,2).map(row=>node('div',`⌖ ${row.nombre}`,'destination-summary-item')));
  if (!active.length) $('destination-summary').append(node('p',admin()?'Agrega la primera organización en Destinos.':'El administrador todavía no ha publicado destinos.'));
  const onboarding = $('onboarding'); onboarding.replaceChildren();
  if (!myProfile() && !admin()) {
    onboarding.append(node('h3','Completa tu perfil para comenzar'),node('p','Necesitamos tu nombre y datos de contacto para coordinar tus donaciones.'),button('Completar mi perfil',()=>editProfile(null,false),'primary'));
  } else if (myProfile() && !myProfile().activo && !admin()) {
    onboarding.append(node('h3','Tu perfil está inactivo'),node('p','Puedes consultar tu historial. Contacta al administrador para registrar nuevas donaciones.'));
  } else if (admin() && !active.length) {
    onboarding.append(node('h3','Publica el primer destino'),node('p','Agrega una organización con su dirección y contacto para que los donantes puedan seleccionarla.'),button('Agregar organización',()=>editOrganization(),'primary'));
  }
  onboarding.hidden = onboarding.childElementCount === 0;
}
function renderOrganizations() {
  $('organizations').replaceChildren();
  for (const organization of state.organizations) {
    const card = node('article',null,'card organization-card');
    card.append(node('div','⌖','organization-icon'),node('span',organization.activo ? 'Recibe donaciones' : 'Inactiva','pill'),node('h2',organization.nombre),node('p',organization.descripcion,'description'),field('Dirección de recepción',organization.direccion),node('p',`Contacto: ${organization.contacto}`,'contact'));
    const actions = node('div',null,'card-actions');
    if (organization.activo) actions.append(button('Donar a este destino',()=>newDonation(organization.id),'primary'));
    if (admin()) {
      actions.append(button('Editar',()=>editOrganization(organization)),button(organization.activo ? 'Desactivar' : 'Activar',async()=>{
        await api(`/api/organizaciones/${organization.id}/estado`,{method:'PATCH',body:JSON.stringify({activo:!organization.activo})}); await refresh(); notify('Organización actualizada.');
      }));
    }
    card.append(actions); $('organizations').append(card);
  }
  if (!state.organizations.length) $('organizations').append(empty('Todavía no hay destinos',admin()?'Registra las organizaciones que podrán recibir donaciones.':'Pronto podrás consultar aquí las organizaciones registradas por el administrador.',admin()?'Agregar organización':null,()=>editOrganization()));
}
function renderProfile() {
  const profile = myProfile(); $('profile-card').replaceChildren();
  if (!profile) { $('profile-card').append(empty('Vamos a conocerte','Completa tu perfil de donante para registrar aportes y coordinar las entregas.','Completar mi perfil',()=>editProfile(null,false))); return; }
  const header = node('div',null,'profile-name'), heading = node('div');
  heading.append(node('h2',profile.nombre),node('p',`${profile.tipo === 'empresa' ? 'Empresa' : 'Persona'} · ${profile.activo ? 'Perfil activo' : 'Perfil inactivo'}`));
  header.append(node('span',profile.nombre.slice(0,1),'avatar'),heading);
  const fields = node('div',null,'profile-fields');
  fields.append(field('Correo electrónico',profile.email),field('Teléfono',profile.telefono),field('Dirección',profile.direccion),field('Miembro desde',dateText(profile.creado)));
  $('profile-card').append(header,fields);
  if (profile.activo || admin()) { const actions = node('div',null,'card-actions'); actions.append(button('Editar mi perfil',()=>editProfile(profile),'primary')); $('profile-card').append(actions); }
}
function renderDonors() {
  $('donor-list').replaceChildren(); if (!admin()) return;
  for (const donor of state.donors) {
    const card = node('article',null,'card');
    const count = state.donations.filter(d=>d.donante_id===donor.id).length;
    card.append(node('h2',donor.nombre),node('span',donor.activo?'Activo':'Inactivo','pill'),node('p',`${donor.email}\n${donor.telefono}`,'donor-meta'),node('p',`${count} donaciones registradas`));
    const actions = node('div',null,'card-actions');
    actions.append(button('Editar',()=>editProfile(donor)),button(donor.activo?'Desactivar':'Activar',async()=>{
      await api(`/api/donantes/${donor.id}/estado`,{method:'PATCH',body:JSON.stringify({activo:!donor.activo})}); await refresh(); notify('Perfil actualizado.');
    }),button('Ver donaciones',()=>{ $('donation-search').value = donor.nombre; $('state-filter').value=''; renderHistory(); navigate('donations'); }));
    if (!count) actions.append(button('Eliminar',async()=>{
      if (!confirm(`¿Eliminar el perfil de ${donor.nombre}? La cuenta de acceso se conserva.`)) return;
      await api(`/api/donantes/${donor.id}`,{method:'DELETE'}); await refresh(); notify('Perfil eliminado.');
    },'danger-button'));
    card.append(actions); $('donor-list').append(card);
  }
  if (!state.donors.length) $('donor-list').append(empty('Todavía no hay donantes','Registra un perfil para una cuenta existente o pide al usuario completar su perfil.','Registrar donante',()=>editProfile()));
}
function render() {
  $('nav-count').textContent = state.donations.length;
  $('welcome').textContent = `Hola, ${myProfile()?.nombre.split(' ')[0] || state.user.username}`;
  renderHome(); renderHistory(); renderOrganizations(); renderProfile(); renderDonors();
}
function localDate(date) { return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`; }
function updateDestination() {
  const destination = state.organizations.find(o=>o.id===Number($('organization-select').value));
  $('selected-destination').textContent = destination ? `Destino: ${destination.nombre}\n${destination.direccion}\nContacto: ${destination.contacto}` : '';
}
function updatePickup() {
  const pickup = $('delivery-mode').value === 'recoleccion';
  $('pickup-label').hidden = !pickup; $('pickup-address').required = pickup;
  if (!pickup) $('pickup-address').value = '';
  else if (!$('pickup-address').value) $('pickup-address').value = myProfile()?.direccion || '';
}
function newDonation(destinationId = null) {
  if (!admin() && !myProfile()) { navigate('profile'); editProfile(null,false); notify('Primero completa tu perfil de donante.'); return; }
  if (!admin() && !myProfile().activo) { notify('Tu perfil está inactivo. Contacta al administrador.'); return; }
  if (admin() && !state.donors.some(d=>d.activo)) { navigate('donors'); notify('Primero registra un donante activo.'); return; }
  const active = state.organizations.filter(o=>o.activo);
  if (!active.length) { navigate('destinations'); notify(admin()?'Agrega una organización antes de registrar donaciones.':'El administrador debe publicar una organización de destino.'); return; }
  $('donation-form').reset();
  fillSelect('organization-select',active,row=>row.nombre);
  if (destinationId) $('organization-select').value=destinationId;
  $('donation-owner-label').hidden = !admin(); $('donation-owner').disabled = !admin();
  fillSelect('donation-owner',state.donors.filter(d=>d.activo),row=>row.nombre);
  const today = new Date(), maximum = new Date(); maximum.setDate(today.getDate()+365);
  $('planned-date').min = localDate(today); $('planned-date').max=localDate(maximum); $('planned-date').value=localDate(today);
  updateDestination(); updatePickup(); openDialog('donation-modal');
}
function editProfile(profile = null, chooseOwner = true) {
  state.profileId = profile?.id || null; $('profile-form').reset();
  state.profileForSelf = !chooseOwner;
  $('profile-form-title').textContent = profile ? 'Editar perfil de donante' : 'Registrar perfil de donante';
  $('profile-owner-label').hidden = !admin() || Boolean(profile) || !chooseOwner;
  fillSelect('profile-owner',state.accounts.filter(account=>!state.donors.some(d=>d.usuario_id===account.id)),row=>row.username);
  if (profile) for (const name of ['nombre','email','telefono','direccion','tipo']) $('profile-form').elements[name].value=profile[name];
  openDialog('profile-modal');
}
function editOrganization(organization = null) {
  state.organizationId = organization?.id || null; $('organization-form').reset();
  $('organization-form-title').textContent=organization?'Editar organización':'Agregar organización';
  if (organization) for (const name of ['nombre','direccion','descripcion','contacto']) $('organization-form').elements[name].value=organization[name];
  openDialog('organization-modal');
}
async function showDetail(identifier) {
  const donation = await api(`/api/donaciones/${identifier}`);
  $('detail-folio').textContent=donation.folio; $('detail-title').textContent=donation.titulo;
  const content = $('detail-content'); content.replaceChildren(pill(donation.estado));
  const destination = node('div',null,'detail-destination');
  destination.append(node('span','DESTINO DE TU DONACIÓN','eyebrow'),node('h3',donation.destino_nombre),node('p',donation.destino_direccion)); content.append(destination);
  const information = node('div',null,'detail-grid');
  information.append(field('Contenido',`${donation.cantidad} ${donation.unidad} · ${categoryLabels[donation.categoria]}`),field('Fecha propuesta',dateText(donation.fecha_prevista)),field('Modalidad',donation.modalidad==='recoleccion'?'Recolección solicitada':'Entrega en sede'),field('Donante',donation.donante_nombre));
  if (donation.modalidad==='recoleccion') information.append(field('Dirección de recolección',donation.direccion_recoleccion,'full'));
  if (donation.descripcion) information.append(field('Descripción e indicaciones',donation.descripcion,'full'));
  content.append(information,node('h3','Seguimiento de la donación'));
  const timeline = node('ol',null,'timeline');
  for (const event of donation.seguimiento) { const entry = node('li'); entry.append(node('h3',labels[event.estado]),node('p',event.nota),node('time',dateText(event.fecha,true))); timeline.append(entry); }
  content.append(timeline);
  if (donation.acciones.length) {
    const actions = node('div',null,'dialog-actions');
    for (const target of donation.acciones) actions.append(button(actionLabels[target],()=>{
      state.statusChange={id:donation.id,target}; $('status-form').reset();
      $('status-summary').textContent=`${donation.folio} · ${actionLabels[target]}`;
      $('status-note').required=['rechazada','cancelada'].includes(target);
      $('status-note').minLength=$('status-note').required ? 5 : 0;
      openDialog('status-modal');
    },['rechazada','cancelada'].includes(target)?'danger-button':'primary'));
    content.append(actions);
  }
  openDialog('detail-modal');
}
function handleForm(id, action) {
  $(id).addEventListener('submit',async event=>{
    event.preventDefault(); const form=event.currentTarget, submit=form.querySelector('[type=submit]'), error=form.querySelector('.form-error');
    if (submit.disabled) return;
    submit.disabled=true; error.textContent='';
    try { await action(Object.fromEntries(new FormData(form))); }
    catch (exception) { error.textContent=exception.message; if (!state.user && id!=='login-form') $('login-error').textContent=exception.message; }
    finally { submit.disabled=false; }
  });
}
handleForm('login-form',async data=>{
  notify('');
  const response=await api('/api/auth/login',{method:'POST',body:JSON.stringify(data)});
  state.token=response.token; state.user=response.usuario; state.generation++;
  try { await refresh(); } catch (error) { logout(); throw error; }
  $('login-form').reset(); $('login-view').hidden=true; $('application').hidden=false;
  $('account-name').textContent=state.user.username; $('account-role').textContent=admin()?'Administrador':'Donante';
  $('avatar').textContent=state.user.username[0].toUpperCase();
  document.querySelectorAll('.admin-only').forEach(element=>{element.hidden=!admin();});
  $('nav-donations').textContent=admin()?'Donaciones':'Mis donaciones';
  $('donations-title').textContent=admin()?'Todas las donaciones':'Mis donaciones';
  $('welcome-subtitle').textContent=admin()?'Gestiona los aportes, coordina destinos y confirma las entregas.':'Gracias por ser parte de algo que ayuda a los demás.';
  navigate('home');
});
handleForm('donation-form',async data=>{
  data.organizacion_id=Number(data.organizacion_id); data.cantidad=Number(data.cantidad);
  if (admin()) data.donante_id=Number(data.donante_id);
  const donation=await api('/api/donaciones',{method:'POST',body:JSON.stringify(data)});
  $('donation-modal').close(); $('donation-search').value=''; $('state-filter').value='';
  await refresh(); navigate('donations'); await showDetail(donation.id); notify(`Donación ${donation.folio} registrada. ¡Gracias por ayudar!`);
});
handleForm('profile-form',async data=>{
  if (admin() && !state.profileId) data.usuario_id=state.profileForSelf?state.user.id:Number($('profile-owner').value);
  await api(state.profileId?`/api/donantes/${state.profileId}`:'/api/donantes',{method:state.profileId?'PUT':'POST',body:JSON.stringify(data)});
  $('profile-modal').close(); await refresh(); notify('Perfil guardado correctamente.');
});
handleForm('organization-form',async data=>{
  await api(state.organizationId?`/api/organizaciones/${state.organizationId}`:'/api/organizaciones',{method:state.organizationId?'PUT':'POST',body:JSON.stringify(data)});
  $('organization-modal').close(); await refresh(); notify('Organización guardada. Ya puedes seleccionarla como destino.');
});
handleForm('status-form',async data=>{
  const change=state.statusChange;
  await api(`/api/donaciones/${change.id}/estado`,{method:'PATCH',body:JSON.stringify({estado:change.target,nota:data.nota})});
  $('status-modal').close(); await refresh(); await showDetail(change.id); notify('Seguimiento actualizado.');
});
document.querySelectorAll('[data-page]').forEach(element=>element.addEventListener('click',()=>navigate(element.dataset.page)));
document.querySelectorAll('[data-new-donation]').forEach(element=>element.addEventListener('click',()=>newDonation()));
document.querySelectorAll('[data-close]').forEach(element=>element.addEventListener('click',()=>element.closest('dialog').close()));
$('logout').addEventListener('click',()=>{logout();notify('Sesión cerrada.');});
$('new-organization').addEventListener('click',()=>editOrganization());
$('new-donor').addEventListener('click',()=>editProfile());
$('organization-select').addEventListener('change',updateDestination);
$('delivery-mode').addEventListener('change',updatePickup);
$('donation-search').addEventListener('input',renderHistory);
$('state-filter').addEventListener('change',renderHistory);
$('refresh').addEventListener('click',async()=>{try {await refresh();notify('Información actualizada.');}catch(error){notify(error.message);}});
