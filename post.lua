local i = 0
request = function()
  i = i + 1
  local id = tostring(os.clock()):gsub("%.", "") .. tostring(i)
  return wrk.format("POST", "/users",
    {["Content-Type"] = "application/json"},
    '{"name": "u' .. id .. '", "email": "' .. id .. '@t.com"}'
  )
end