// Trusted learner JavaScript. A fresh Node process runs each exercise.
const fs = require('node:fs');
const vm = require('node:vm');
const {isDeepStrictEqual} = require('node:util');
const request=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const result={error:null,checks:[],passed:false};
const context=vm.createContext({console,require,process,Buffer,setTimeout,clearTimeout,equal:(a,b)=>isDeepStrictEqual(JSON.parse(JSON.stringify(a)),JSON.parse(JSON.stringify(b)))});
try {
  vm.runInContext(request.code,context,{filename:'exercise.js',timeout:40000});
  for(const check of request.checks) {
    let passed=false,detail='';
    try { passed=Boolean(vm.runInContext(check.expr,context,{timeout:5000})); if(!passed)detail='The result did not match this requirement. Try a hint or inspect your output.'; }
    catch(e){detail=String(e).slice(0,1200);}
    result.checks.push({label:check.label,passed,detail});
  }
  result.passed=result.checks.length>0&&result.checks.every(c=>c.passed);
} catch(e){result.error=String(e.stack||e).slice(-6000);}
fs.writeFileSync(process.argv[3],JSON.stringify(result));
