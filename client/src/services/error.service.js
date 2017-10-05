const Service = ($q) => {
  function response(data) {
    if (data.data && data.data.status === 'failure') {
      return $q.reject(data.data.errors);
    }
    return data.data;
  }

  const service = {
    response,
  };

  return service;
};

export default Service;
