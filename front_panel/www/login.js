'use strict';
if (new URLSearchParams(location.search).get('role') === 'editor') document.querySelector('#role').value='editor';
function keyboardMode(){const input=document.querySelector('#password'),viewer=document.querySelector('#role').value==='viewer';input.inputMode=viewer?'numeric':'text';input.minLength=viewer?6:16;}
document.querySelector('#role').addEventListener('change',keyboardMode);keyboardMode();
document.querySelector('#login-form').addEventListener('submit',async event=>{
 event.preventDefault();const button=event.target.querySelector('button');button.disabled=true;
 try{const role=document.querySelector('#role').value;const response=await fetch('./api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({role,password:document.querySelector('#password').value})});
 const body=await response.json();if(!response.ok)throw new Error(body.error||'접속 실패');location.href=role==='editor'?'./editor':'./';
 }catch(error){document.querySelector('#message').textContent=error.message;}finally{button.disabled=false;}
});
