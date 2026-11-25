import test from 'node:test'
import assert from 'node:assert/strict'
import {parseWorkspaceRoute,goToSection} from '../src/workspaceRoute.ts'

test('section links restore the page and selected tree',()=>{
  assert.deepEqual(parseWorkspaceRoute('#/insights/2'),{page:'insights',treeId:2})
  assert.deepEqual(parseWorkspaceRoute('#/settings'),{page:'settings',treeId:null})
  assert.deepEqual(parseWorkspaceRoute(''),{page:'overview',treeId:null})
  assert.deepEqual(parseWorkspaceRoute('#/detail/bad'),{page:'overview',treeId:null})
})

test('navigation preserves the base address and avoids duplicate entries',()=>{
  const location=new URL('https://test.invalid/?lang=bg')
  const calls=[]
  const record=(method,url)=>{calls.push(method);location.href=url.href}
  globalThis.window={location,dispatchEvent(){},history:{
    pushState(_state,_title,url){record('push',url)},
    replaceState(_state,_title,url){record('replace',url)},
  }}
  try{
    goToSection('service',2)
    assert.equal(location.href,'https://test.invalid/?lang=bg#/service/2')
    goToSection('service',2)
    goToSection('service',3,true)
    assert.deepEqual(calls,['push','replace'])
  }finally{delete globalThis.window}
})
