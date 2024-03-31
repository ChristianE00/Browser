
// Used to lookup handles and event types
LISTENERS = {}
console = { log: function(x) { call_python("log", x); } }

document = { 

  querySelectorAll: function(s) {
    var handles = call_python("querySelectorAll", s);
    var h = handles.map(function(h) {return new Node(h) });
    if(h)
      console.log('!dbg[querySelectorAll]: h is NOTE null');
    else
      console.log('!dbg[querySelectorAll]: h is null');
    return h},

  createElement: function(tagName) {
    var n = Node(call_python("createElement", tagName));
    if (n)
      console.log('!dbg[createElement]: n is NOT null.');
    else
      console.log('!dbg[createElement]: n is null.');
    return n
  }

}


// ---OBJECT

Object.defineProperty(Node.prototype, 'innerHTML', {
  set: function(s) {
    call_python("innerHTML_set", this.handle, s.toString());
  }
});

Object.defineProperty(Node.prototype, 'children', {
  get: function(s) {
    var handles = call_python("getChildren", this.handle);
    return handles.map(function(h) { return new Node(h); });
  }
});

// ---EVENT

function Event(type) {
  this.type = type
  this.do_default = true;
}

Event.prototype.preventDefault = function() {
  this.do_default = false;
}


// ---NODE



function Node(handle) { this.handle = handle; }

Node.prototype.getAttribute = function(attr) {
  console.log("!dbg BEFORE getAttribute");
  return call_python('getAttribute', this.handle, attr);
}

Node.prototype.appendChild = function(child){
  console.log(" BEFORE appendChild");
  if (child && child.handle){
    console.log('![appendChild]: child is NOT null.');
    call_python('appendChild', this.handle, child.handle);
  }
  else{
    console.log('!dbg[appendChild]: ERROR, child is null.');
  }
}

Node.prototype.insertBefore = function(child, sibling){
  console.log("!dbg BEFORE INSERTBEFORE");
  if (child && sibling){
    call_python('insertBefore', this.handle, child.handle, sibling.handle);
    console.log("!dbg [insertBefore]: child & sibling are NOT null.");
  }
  else if(!child){
    console.log("!dbg [insertBefore]: ERROR, child is null.");
  }

  else{
    console.log("!dbg [insertBefore]: ERROR, sibling is null.");
    //call_python('insertBefore', this.handle, child.handle);
  }
}

Node.prototype.addEventListener = function(type, listener) {
  if (!LISTENERS[this.handle]) LISTENERS[this.handle] = {};
  var dict = LISTENERS[this.handle];
  if (!dict[type]) dict[type] = [];
  var list = dict[type];
  list.push(listener);
}

Node.prototype.dispatchEvent = function(evt) {
  var type = evt.type;
  var handle = this.handle;
  var list = (LISTENERS[handle] && LISTENERS[handle][type]) || [];
  for (var i = 0; i < list.length; i++) {
    list[i].call(this, evt);
  }
  return evt.do_default;
}




