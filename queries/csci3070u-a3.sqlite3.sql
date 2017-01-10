WITH R AS
(SELECT S.instructor as X, T.instructor as Y, count(distinct S.code) as WEIGHT
FROM schedule S join schedule T
ON S.code = T.code
   AND S.instructor IS NOT 'TBA'
   AND T.instructor IS NOT 'TBA'
   AND S.instructor NOT LIKE 'X %'
   AND T.instructor NOT LIKE 'X %'
   AND S.instructor < T.instructor
   AND S.semester >= '201109'
   AND T.semester >= '201109'
GROUP BY X, Y
ORDER BY WEIGHT DESC)
SELECT COUNT(DISTINCT A) 
FROM (SELECT X as A from R UNION SELECT Y as A FROM R);
