from requests import get

print(get('http://tco.kosmogor.xyz/api/news').json())
print(get('http://tco.kosmogor.xyz/api/news/1').json())

print(get('http://tco.kosmogor.xyz/api/news/999').json())