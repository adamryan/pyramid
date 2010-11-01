import copy

from webob import Response

from zope.configuration.xmlconfig import _clearContext

from zope.interface import implements
from zope.interface import Interface
from zope.interface import alsoProvides

from pyramid.interfaces import IRequest
from pyramid.interfaces import ISecuredView
from pyramid.interfaces import IView
from pyramid.interfaces import IViewClassifier

from pyramid.configuration import Configurator
from pyramid.exceptions import Forbidden
from pyramid.registry import Registry
from pyramid.security import Authenticated
from pyramid.security import Everyone
from pyramid.security import has_permission
from pyramid.threadlocal import get_current_registry
from pyramid.threadlocal import manager
from pyramid.zcml import zcml_configure # API

zcml_configure # prevent pyflakes from complaining

_marker = object()

def registerDummySecurityPolicy(userid=None, groupids=(), permissive=True):
    """ Registers a pair of faux :mod:`pyramid` security policies:
    a :term:`authentication policy` and a :term:`authorization
    policy`.

    The behavior of the registered :term:`authorization policy`
    depends on the ``permissive`` argument.  If ``permissive`` is
    true, a permissive :term:`authorization policy` is registered;
    this policy allows all access.  If ``permissive`` is false, a
    nonpermissive :term:`authorization policy` is registered; this
    policy denies all access.

    The behavior of the registered :term:`authentication policy`
    depends on the values provided for the ``userid`` and ``groupids``
    argument.  The authentication policy will return the userid
    identifier implied by the ``userid`` argument and the group ids
    implied by the ``groupids`` argument when the
    :func:`pyramid.security.authenticated_userid` or 
    :func:`pyramid.security.effective_principals` APIs are used.

    This function is most useful when testing code that uses the APIs
    named :func:`pyramid.security.has_permission`,
    :func:`pyramid.security.authenticated_userid`,
    :func:`pyramid.security.effective_principals`, and
    :func:`pyramid.security.principals_allowed_by_permission`.

    .. warning:: This API is deprecated as of :mod:`pyramid` 1.0.
       Instead use the
       :meth:`pyramid.configuration.Configurator.testing_securitypolicy`
       method in your unit and integration tests.
    """
    registry = get_current_registry()
    config = Configurator(registry=registry)
    return config.testing_securitypolicy(userid=userid, groupids=groupids,
                                         permissive=permissive)

def registerModels(models):
    """ Registers a dictionary of :term:`model` objects that can be
    resolved via the :func:`pyramid.traversal.find_model` API.

    The :func:`pyramid.traversal.find_model` API is called with a
    path as one of its arguments.  If the dictionary you register when
    calling this method contains that path as a string key
    (e.g. ``/foo/bar`` or ``foo/bar``), the corresponding value will
    be returned to ``find_model`` (and thus to your code) when
    :func:`pyramid.traversal.find_model` is called with an
    equivalent path string or tuple.

    .. warning:: This API is deprecated as of :mod:`pyramid` 1.0.
       Instead use the
       :meth:`pyramid.configuration.Configurator.testing_models`
       method in your unit and integration tests.
    """
    registry = get_current_registry()
    config = Configurator(registry=registry)
    return config.testing_models(models)

def registerEventListener(event_iface=None):
    """ Registers an :term:`event` listener (aka :term:`subscriber`)
    listening for events of the type ``event_iface``.  This method
    returns a list object which is appended to by the subscriber
    whenever an event is captured.

    When an event is dispatched that matches ``event_iface``, that
    event will be appended to the list.  You can then compare the
    values in the list to expected event notifications.  This method
    is useful when testing code that wants to call
    :meth:`pyramid.registry.Registry.notify`,
    :func:`zope.component.event.dispatch` or
    :func:`zope.component.event.objectEventNotify`.

    The default value of ``event_iface`` (``None``) implies a
    subscriber registered for *any* kind of event.

    .. warning:: This API is deprecated as of :mod:`pyramid` 1.0.
       Instead use the
       :meth:`pyramid.configuration.Configurator.testing_add_subscriber`
       method in your unit and integration tests.
    """
    registry = get_current_registry()
    config = Configurator(registry=registry)
    return config.testing_add_subscriber(event_iface)

def registerTemplateRenderer(path, renderer=None):
    """ Register a template renderer at ``path`` (usually a relative
    filename ala ``templates/foo.pt``) and return the renderer object.
    If the ``renderer`` argument is None, a 'dummy' renderer will be
    used.  This function is useful when testing code that calls the
    :func:`pyramid.renderers.render` function or
    :func:`pyramid.renderers.render_to_response` function or any
    other ``render_*`` or ``get_*`` API of the
    :mod:`pyramid.renderers` module.

    .. warning:: This API is deprecated as of :mod:`pyramid` 1.0.
       Instead use the
       :meth:`pyramid.configuration.Configurator.testing_add_template``
       method in your unit and integration tests.

    """
    registry = get_current_registry()
    config = Configurator(registry=registry)
    return config.testing_add_template(path, renderer)

# registerDummyRenderer is a deprecated alias that should never be removed
# (too much usage in the wild)
registerDummyRenderer = registerTemplateRenderer

def registerView(name, result='', view=None, for_=(Interface, Interface),
                 permission=None):
    """ Registers a :mod:`pyramid` :term:`view callable` under the
    name implied by the ``name`` argument.  The view will return a
    :term:`WebOb` :term:`Response` object with the value implied by
    the ``result`` argument as its ``body`` attribute.  To gain more
    control, if you pass in a non-``None`` ``view`` argument, this
    value will be used as a view callable instead of an automatically
    generated view callable (and ``result`` is not used).

    To protect the view using a :term:`permission`, pass in a
    non-``None`` value as ``permission``.  This permission will be
    checked by any active :term:`authorization policy` when view
    execution is attempted.

    This function is useful when testing code which calls
    :func:`pyramid.view.render_view_to_response`.

    .. warning:: This API is deprecated as of :mod:`pyramid` 1.0.
       Instead use the
       :meth:`pyramid.configuration.Configurator.add_view``
       method in your unit and integration tests.
    """
    for_ = (IViewClassifier, ) + for_
    if view is None:
        def view(context, request):
            return Response(result)
    if permission is None:
        return registerAdapter(view, for_, IView, name)
    else:
        def _secure(context, request):
            if not has_permission(permission, context, request):
                raise Forbidden('no permission')
            else:
                return view(context, request)
        _secure.__call_permissive__ = view
        def permitted(context, request):
            return has_permission(permission, context, request)
        _secure.__permitted__ = permitted
        return registerAdapter(_secure, for_, ISecuredView, name)

def registerUtility(impl, iface=Interface, name=''):
    """ Register a ZCA utility component.

    The ``impl`` argument specifies the implementation of the utility.
    The ``iface`` argument specifies the :term:`interface` which will
    be later required to look up the utility
    (:class:`zope.interface.Interface`, by default).  The ``name``
    argument implies the utility name; it is the empty string by
    default.

    See `The ZCA book <http://www.muthukadan.net/docs/zca.html>`_ for
    more information about ZCA utilities.

    .. warning:: This API is deprecated as of :mod:`pyramid` 1.0.
       Instead use the :meth:`pyramid.Registry.registerUtility`
       method.  The ``registry`` attribute of a :term:`Configurator`
       in your unit and integration tests is an instance of the
       :class:`pyramid.Registry` class.
    """
    reg = get_current_registry()
    reg.registerUtility(impl, iface, name=name)
    return impl

def registerAdapter(impl, for_=Interface, provides=Interface, name=''):
    """ Register a ZCA adapter component.

    The ``impl`` argument specifies the implementation of the
    component (often a class).  The ``for_`` argument implies the
    ``for`` interface type used for this registration; it is
    :class:`zope.interface.Interface` by default.  If ``for`` is not a
    tuple or list, it will be converted to a one-tuple before being
    passed to underlying :meth:`pyramid.registry.registerAdapter`
    API.

    The ``provides`` argument specifies the ZCA 'provides' interface,
    :class:`zope.interface.Interface` by default.

    The ``name`` argument is the empty string by default; it implies
    the name under which the adapter is registered.
    
    See `The ZCA book <http://www.muthukadan.net/docs/zca.html>`_ for
    more information about ZCA adapters.

    .. warning:: This API is deprecated as of :mod:`pyramid` 1.0.
       Instead use the :meth:`pyramid.Registry.registerAdapter`
       method.  The ``registry`` attribute of a :term:`Configurator`
       in your unit and integration tests is an instance of the
       :class:`pyramid.Registry` class.
    """
    reg = get_current_registry()
    if not isinstance(for_, (tuple, list)):
        for_ = (for_,)
    reg.registerAdapter(impl, for_, provides, name=name)
    return impl

def registerSubscriber(subscriber, iface=Interface):
    """ Register a ZCA subscriber component.

    The ``subscriber`` argument specifies the implementation of the
    subscriber component (often a function).

    The ``iface`` argument is the interface type for which the
    subscriber will be registered (:class:`zope.interface.Interface`
    by default). If ``iface`` is not a tuple or list, it will be
    converted to a one-tuple before being passed to the underlying ZCA
    :meth:`pyramid.registry.registerHandler` method.

    See `The ZCA book <http://www.muthukadan.net/docs/zca.html>`_ for
    more information about ZCA subscribers.

    .. warning:: This API is deprecated as of :mod:`pyramid` 1.0.
       Instead use the
       :meth:`pyramid.configuration.Configurator.add_subscriber`
       method in your unit and integration tests.
    """
    registry = get_current_registry()
    config = Configurator(registry)
    return config.add_subscriber(subscriber, iface=iface)

def registerRoute(pattern, name, factory=None):
    """ Register a new :term:`route` using a pattern
    (e.g. ``:pagename``), a name (e.g. ``home``), and an optional root
    factory.

    The ``pattern`` argument implies the route pattern.  The ``name``
    argument implies the route name.  The ``factory`` argument implies
    a :term:`root factory` associated with the route.

    This API is useful for testing code that calls
    e.g. :func:`pyramid.url.route_url`.

    .. warning:: This API is deprecated as of :mod:`pyramid` 1.0.
       Instead use the
       :meth:`pyramid.configuration.Configurator.add_route`
       method in your unit and integration tests.
    """
    reg = get_current_registry()
    config = Configurator(registry=reg)
    return config.add_route(name, pattern, factory=factory)

def registerSettings(dictarg=None, **kw):
    """Register one or more 'setting' key/value pairs.  A setting is
    a single key/value pair in the dictionary-ish object returned from
    the API :func:`pyramid.settings.get_settings`.

    You may pass a dictionary::

       registerSettings({'external_uri':'http://example.com'})

    Or a set of key/value pairs::
    
       registerSettings(external_uri='http://example.com')

    Use of this function is required when you need to test code that
    calls the :func:`pyramid.settings.get_settings` API and which
    uses return values from that API.

    .. warning:: This API is deprecated as of :mod:`pyramid` 1.0.
       Instead use the
       :meth:`pyramid.configuration.Configurator.add_settings`
       method in your unit and integration tests.
    """
    registry = get_current_registry()
    config = Configurator(registry=registry)
    config.add_settings(dictarg, **kw)

class DummyRootFactory(object):
    __parent__ = None
    __name__ = None
    def __init__(self, request):
        if 'bfg.routes.matchdict' in request:
            self.__dict__.update(request['bfg.routes.matchdict'])

class DummySecurityPolicy(object):
    """ A standin for both an IAuthentication and IAuthorization policy """
    def __init__(self, userid=None, groupids=(), permissive=True):
        self.userid = userid
        self.groupids = groupids
        self.permissive = permissive

    def authenticated_userid(self, request):
        return self.userid

    def effective_principals(self, request):
        effective_principals = [Everyone]
        if self.userid:
            effective_principals.append(Authenticated)
            effective_principals.append(self.userid)
            effective_principals.extend(self.groupids)
        return effective_principals

    def remember(self, request, principal, **kw):
        return []

    def forget(self, request):
        return []

    def permits(self, context, principals, permission):
        return self.permissive

    def principals_allowed_by_permission(self, context, permission):
        return self.effective_principals(None)

class DummyTemplateRenderer(object):
    """
    An instance of this class is returned from
    :func:`pyramid.testing.registerTemplateRenderer`.  It has a
    helper function (``assert_``) that makes it possible to make an
    assertion which compares data passed to the renderer by the view
    function against expected key/value pairs.
    """

    def __init__(self, string_response=''):
        self._received = {}
        self._string_response = string_response
        self._implementation = MockTemplate(string_response)

    # For in-the-wild test code that doesn't create its own renderer,
    # but mutates our internals instead.  When all you read is the
    # source code, *everything* is an API!
    def _get_string_response(self):
        return self._string_response
    def _set_string_response(self, response):
        self._string_response = response
        self._implementation.response = response
    string_response = property(_get_string_response, _set_string_response)

    def implementation(self):
        return self._implementation
    
    def __call__(self, kw, system=None):
        if system:
            self._received.update(system)
        self._received.update(kw)
        return self.string_response

    def __getattr__(self, k):
        """ Backwards compatibility """
        val = self._received.get(k, _marker)
        if val is _marker:
            val = self._implementation._received.get(k, _marker)
            if val is _marker:
                raise AttributeError(k)
        return val

    def assert_(self, **kw):
        """ Accept an arbitrary set of assertion key/value pairs.  For
        each assertion key/value pair assert that the renderer
        (eg. :func:`pyramid.renderer.render_to_response`)
        received the key with a value that equals the asserted
        value. If the renderer did not receive the key at all, or the
        value received by the renderer doesn't match the assertion
        value, raise an :exc:`AssertionError`."""
        for k, v in kw.items():
            myval = self._received.get(k, _marker)
            if myval is _marker:
                myval = self._implementation._received.get(k, _marker)
                if myval is _marker:
                    raise AssertionError(
                        'A value for key "%s" was not passed to the renderer'
                        % k)
                    
            if myval != v:
                raise AssertionError(
                    '\nasserted value for %s: %r\nactual value: %r' % (
                    v, k, myval))
        return True

class DummyModel:
    """ A dummy :mod:`pyramid` :term:`model` object."""
    def __init__(self, __name__=None, __parent__=None, __provides__=None,
                 **kw):
        """ The model's ``__name__`` attribute will be set to the
        value of the ``__name__`` argument, and the model's
        ``__parent__`` attribute will be set to the value of the
        ``__parent__`` argument.  If ``__provides__`` is specified, it
        should be an interface object or tuple of interface objects
        that will be attached to the resulting model via
        :func:`zope.interface.alsoProvides`. Any extra keywords passed
        in the ``kw`` argumnent will be set as direct attributes of
        the model object."""
        self.__name__ = __name__
        self.__parent__ = __parent__
        if __provides__ is not None:
            alsoProvides(self, __provides__)
        self.kw = kw
        self.__dict__.update(**kw)
        self.subs = {}

    def __setitem__(self, name, val):
        """ When the ``__setitem__`` method is called, the object
        passed in as ``val`` will be decorated with a ``__parent__``
        attribute pointing at the dummy model and a ``__name__``
        attribute that is the value of ``name``.  The value will then
        be returned when dummy model's ``__getitem__`` is called with
        the name ``name```."""
        val.__name__ = name
        val.__parent__ = self
        self.subs[name] = val
        
    def __getitem__(self, name):
        """ Return a named subobject (see ``__setitem__``)"""
        ob = self.subs[name]
        return ob

    def __delitem__(self, name):
        del self.subs[name]

    def get(self, name, default=None):
        return self.subs.get(name, default)

    def values(self):
        """ Return the values set by __setitem__ """
        return self.subs.values()

    def items(self):
        """ Return the items set by __setitem__ """
        return self.subs.items()

    def keys(self):
        """ Return the keys set by __setitem__ """
        return self.subs.keys()

    __iter__ = keys

    def __nonzero__(self):
        return True

    def __len__(self):
        return len(self.subs)

    def __contains__(self, name):
        return name in self.subs
    
    def clone(self, __name__=_marker, __parent__=_marker, **kw):
        """ Create a clone of the model object.  If ``__name__`` or
        ``__parent__`` arguments are passed, use these values to
        override the existing ``__name__`` or ``__parent__`` of the
        model.  If any extra keyword args are passed in via the ``kw``
        argument, use these keywords to add to or override existing
        model keywords (attributes)."""
        oldkw = self.kw.copy()
        oldkw.update(kw)
        inst = self.__class__(self.__name__, self.__parent__, **oldkw)
        inst.subs = copy.deepcopy(self.subs)
        if __name__ is not _marker:
            inst.__name__ = __name__
        if __parent__ is not _marker:
            inst.__parent__ = __parent__
        return inst

class DummyRequest(object):
    """ A dummy request object (imitates a :term:`request` object).
    
    The ``params``, ``environ``, ``headers``, ``path``, and
    ``cookies`` arguments correspond to their :term`WebOb`
    equivalents.

    The ``post`` argument,  if passed, populates the request's
    ``POST`` attribute, but *not* ``params``, in order to allow testing
    that the app accepts data for a given view only from POST requests.
    This argument also sets ``self.method`` to "POST".

    Extra keyword arguments are assigned as attributes of the request
    itself.
    """
    implements(IRequest)
    method = 'GET'
    application_url = 'http://example.com'
    host = 'example.com:80'
    content_length = 0
    response_callbacks = ()
    def __init__(self, params=None, environ=None, headers=None, path='/',
                 cookies=None, post=None, **kw):
        if environ is None:
            environ = {}
        if params is None:
            params = {}
        if headers is None:
            headers = {}
        if cookies is None:
            cookies = {}
        self.environ = environ
        self.headers = headers
        self.params = params
        self.cookies = cookies
        self.matchdict = {}
        self.GET = params
        if post is not None:
            self.method = 'POST'
            self.POST = post
        else:
            self.POST = params
        self.host_url = self.application_url
        self.path_url = self.application_url
        self.url = self.application_url
        self.path = path
        self.path_info = path
        self.script_name = ''
        self.path_qs = ''
        self.body = ''
        self.view_name = ''
        self.subpath = ()
        self.traversed = ()
        self.virtual_root_path = ()
        self.context = None
        self.root = None
        self.virtual_root = None
        self.marshalled = params # repoze.monty
        self.registry = get_current_registry()
        self.__dict__.update(kw)

    def add_response_callback(self, callback):
        if not self.response_callbacks:
            self.response_callbacks = []
        self.response_callbacks.append(callback)

def setUp(registry=None, request=None, hook_zca=True):
    """
    Set :mod:`pyramid` registry and request thread locals for the
    duration of a single unit test.

    Use this function in the ``setUp`` method of a unittest test case
    which directly or indirectly uses:

    - any of the ``register*`` functions in :mod:`pyramid.testing`
      (such as :func:`pyramid.testing.registerModels`)

    - any method of the :class:`pyramid.configuration.Configurator`
      object returned by this function.

    - the :func:`pyramid.threadlocal.get_current_registry` or
      :func:`pyramid.threadlocal.get_current_request` functions.

    If you use the ``testing.register*`` APIs, or the
    ``get_current_*`` functions (or call :mod:`pyramid` code that
    uses these functions) without calling ``setUp``,
    :func:`pyramid.threadlocal.get_current_registry` will return a
    *global* :term:`application registry`, which may cause unit tests
    to not be isolated with respect to registrations they perform.

    If the ``registry`` argument is ``None``, a new empty
    :term:`application registry` will be created (an instance of the
    :class:`pyramid.registry.Registry` class).  If the ``registry``
    argument is not ``None``, the value passed in should be an
    instance of the :class:`pyramid.registry.Registry` class or a
    suitable testing analogue.

    After ``setUp`` is finished, the registry returned by the
    :func:`pyramid.threadlocal.get_current_request` function will
    be the passed (or constructed) registry until
    :func:`pyramid.testing.tearDown` is called (or
    :func:`pyramid.testing.setUp` is called again) .

    If the ``hook_zca`` argument is ``True``, ``setUp`` will attempt
    to perform the operation ``zope.component.getSiteManager.sethook(
    pyramid.threadlocal.get_current_registry)``, which will cause
    the :term:`Zope Component Architecture` global API
    (e.g. :func:`zope.component.getSiteManager`,
    :func:`zope.component.getAdapter`, and so on) to use the registry
    constructed by ``setUp`` as the value it returns from
    :func:`zope.component.getSiteManager`.  If the
    :mod:`zope.component` package cannot be imported, or if
    ``hook_zca`` is ``False``, the hook will not be set.

    This function returns an instance of the
    :class:`pyramid.configuration.Configurator` class, which can be
    used for further configuration to set up an environment suitable
    for a unit or integration test.  The ``registry`` attribute
    attached to the Configurator instance represents the 'current'
    :term:`application registry`; the same registry will be returned
    by :func:`pyramid.threadlocal.get_current_registry` during the
    execution of the test.

    .. warning:: Although this method of setting up a test registry
                 will never disappear, after :mod:`pyramid` 1.0,
                 using the ``begin`` and ``end`` methods of a
                 ``Configurator`` are preferred to using
                 ``pyramid.testing.setUp`` and
                 ``pyramid.testing.tearDown``.  See
                 :ref:`unittesting_chapter` for more information.
    """
    manager.clear()
    if registry is None:
        registry = Registry('testing')
    config = Configurator(registry=registry)
    if hasattr(registry, 'registerUtility'):
        # Sometimes nose calls us with a non-registry object because
        # it thinks this function is module test setup.  Likewise,
        # someone may be passing us an esoteric "dummy" registry, and
        # the below won't succeed if it doesn't have a registerUtility
        # method.
        from pyramid.configuration import DEFAULT_RENDERERS
        for name, renderer in DEFAULT_RENDERERS:
            # Cause the default renderers to be registered because
            # in-the-wild test code relies on being able to call
            # e.g. ``pyramid.chameleon_zpt.render_template``
            # without registering a .pt renderer, expecting the "real"
            # template to be rendered.  This is a holdover from when
            # individual template system renderers weren't indirected
            # by the ``pyramid.renderers`` machinery, and
            # ``render_template`` and friends went behind the back of
            # any existing renderer factory lookup system.
            config.add_renderer(name, renderer)
    hook_zca and config.hook_zca()
    config.begin(request=request)
    return config

def tearDown(unhook_zca=True):
    """Undo the effects :func:`pyramid.testing.setUp`.  Use this
    function in the ``tearDown`` method of a unit test that uses
    :func:`pyramid.testing.setUp` in its ``setUp`` method.

    If the ``unhook_zca`` argument is ``True`` (the default), call
    :func:`zope.component.getSiteManager.reset`.  This undoes the
    action of :func:`pyramid.testing.setUp` called with the
    argument ``hook_zca=True``.  If :mod:`zope.component` cannot be
    imported, ignore the argument.

    .. warning:: Although this method of tearing a test setup down
                 will never disappear, after :mod:`pyramid` 1.0,
                 using the ``begin`` and ``end`` methods of a
                 ``Configurator`` are preferred to using
                 ``pyramid.testing.setUp`` and
                 ``pyramid.testing.tearDown``.  See
                 :ref:`unittesting_chapter` for more information.

    """
    if unhook_zca:
        try:
            from zope.component import getSiteManager
            getSiteManager.reset()
        except ImportError: # pragma: no cover
            pass
    info = manager.pop()
    manager.clear()
    if info is not None:
        registry = info['registry']
        if hasattr(registry, '__init__') and hasattr(registry, '__name__'):
            try:
                registry.__init__(registry.__name__)
            except TypeError:
                # calling __init__ is largely for the benefit of
                # people who want to use the global ZCA registry;
                # however maybe somebody's using a registry we don't
                # understand, let's not blow up
                pass
    _clearContext() # XXX why?

def cleanUp(*arg, **kw):
    """ :func:`pyramid.testing.cleanUp` is an alias for
    :func:`pyramid.testing.setUp`.  Although this function is
    effectively deprecated as of :mod:`pyramid` 1.0, due to its
    extensive production usage, it will never be removed."""
    return setUp(*arg, **kw)

class DummyRendererFactory(object):
    """ Registered by
    ``pyramid.configuration.Configurator.testing_add_renderer`` as
    a dummy renderer factory.  The indecision about what to use as a
    key (a spec vs. a relative name) is caused by test suites in the
    wild believing they can register either.  The ``factory`` argument
    passed to this constructor is usually the *real* template renderer
    factory, found when ``testing_add_renderer`` is called."""
    def __init__(self, name, factory):
        self.name = name
        self.factory = factory # the "real" renderer factory reg'd previously
        self.renderers = {}

    def add(self, spec, renderer):
        self.renderers[spec] = renderer
        if ':' in spec:
            package, relative = spec.split(':', 1)
            self.renderers[relative] = renderer

    def __call__(self, info):
        spec = info.name
        renderer = self.renderers.get(spec)
        if renderer is None:
            if ':' in spec:
                package, relative = spec.split(':', 1)
                renderer = self.renderers.get(relative)
            if renderer is None:
                if self.factory:
                    renderer = self.factory(info)
                else:
                    raise KeyError('No testing renderer registered for %r' %
                                   spec)
        return renderer
            
        
class MockTemplate(object):
    def __init__(self, response):
        self._received = {}
        self.response = response
    def __getattr__(self, attrname):
        return self
    def __getitem__(self, attrname):
        return self
    def __call__(self, *arg, **kw):
        self._received.update(kw)
        return self.response