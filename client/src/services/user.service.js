const Service = ($http, $q, $window) => {
  const admin = {};
  const juror = {};
  let user = {};

  const base = [$window.__env.baseUrl, 'v1'].join('/');

  function getAdmin() {
    return $http
      .get(base + '/admin')
      .then((data) => {
        angular.extend(admin, data);
        angular.extend(user, data.user);
        return data;
      });
  }

  function getJuror() {
    return $http
      .get(base + '/juror')
      .then((data) => {
        angular.extend(juror, data);
        angular.extend(user, data.user);
        return data;
      });
  }

  function login() {
    const current = $window.location.href;
    $window.location.href = `${window.__env.baseUrl}/login?next=${encodeURIComponent(current)}`;
  }

  function logout() {
    user = {};
    return $http
      .get(`${window.__env.baseUrl}/logout`);
  }

  const service = {
    getAdmin,
    getJuror,
    getUser: () => $q.when(user),
    login,
    logout,
  };

  return service;
};

export default Service;
