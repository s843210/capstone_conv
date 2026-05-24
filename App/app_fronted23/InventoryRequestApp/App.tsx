import React, {useEffect, useRef, useState} from 'react';
import {NavigationContainer} from '@react-navigation/native';
import {createNativeStackNavigator} from '@react-navigation/native-stack';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SplashScreen from 'expo-splash-screen';
import {RequestItem, RootStackParamList, Suggestion} from './src/types';
import LoginScreen from './src/screens/LoginScreen';
import ProductListScreen from './src/screens/ProductListScreen';
import ProductDetailScreen from './src/screens/ProductDetailScreen';
import RequestQtyScreen from './src/screens/RequestQtyScreen';
import RequestDoneScreen from './src/screens/RequestDoneScreen';
import MyRequestsScreen from './src/screens/MyRequestsScreen';
import SuggestionsScreen from './src/screens/SuggestionsScreen';
import SuggestionWriteScreen from './src/screens/SuggestionWriteScreen';
import SuggestionDetailScreen from './src/screens/SuggestionDetailScreen';
import SuggestionEditScreen from './src/screens/SuggestionEditScreen';
import {STORAGE_KEYS} from './src/data/appConstants';
import {loadSuggestions, saveSuggestions} from './src/data/suggestionStorage';
import {loginGoogle} from './src/api/authApi';
import {setApiAuthToken} from './src/api/client';
import {deleteStudentRequest, fetchStudentRequests, submitStudentRequest} from './src/api/studentApi';
import {
  createSuggestion,
  deleteSuggestion as deleteSuggestionFromServer,
  deleteSuggestionsBulk as deleteSuggestionsBulkFromServer,
  fetchSuggestions,
  updateSuggestion as updateSuggestionOnServer,
} from './src/api/suggestionApi';

const Stack = createNativeStackNavigator<RootStackParamList>();
const SPLASH_TEST_DELAY_MS = 2000;

SplashScreen.preventAutoHideAsync().catch(() => undefined);

export default function App() {
  const [requests, setRequests] = useState<RequestItem[]>([]);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const suggestionsRef = useRef<Suggestion[]>([]);
  const [currentUser, setCurrentUser] = useState('');
  const [isInitializing, setIsInitializing] = useState(true);

  const syncSuggestionsState = (nextSuggestions: Suggestion[]) => {
    suggestionsRef.current = nextSuggestions;
    setSuggestions(nextSuggestions);
  };

  useEffect(() => {
    const initializeApp = async () => {
      let nextRequests: RequestItem[] = [];
      let nextUser = '';

      try {
        const [storedRequests, storedUser, storedAuthToken, storedSuggestions] = await Promise.all([
          AsyncStorage.getItem(STORAGE_KEYS.requests),
          AsyncStorage.getItem(STORAGE_KEYS.user),
          AsyncStorage.getItem(STORAGE_KEYS.authToken),
          loadSuggestions(),
          new Promise(resolve => setTimeout(resolve, SPLASH_TEST_DELAY_MS)),
        ]);

        if (storedRequests) {
          try {
            const parsed = JSON.parse(storedRequests) as RequestItem[];
            if (Array.isArray(parsed)) {
              nextRequests = parsed;
            }
          } catch {
            nextRequests = [];
          }
        }

        if (storedAuthToken && storedAuthToken.trim()) {
          setApiAuthToken(storedAuthToken.trim());
        }

        if (storedUser && storedUser.trim() && storedAuthToken && storedAuthToken.trim()) {
          nextUser = storedUser.trim();
        }

        syncSuggestionsState(storedSuggestions);
      } catch {
        nextRequests = [];
        nextUser = '';
      } finally {
        setRequests(nextRequests);
        setCurrentUser(nextUser);
        setIsInitializing(false);
        SplashScreen.hideAsync().catch(() => undefined);
      }
    };

    initializeApp();
  }, []);

  useEffect(() => {
    if (isInitializing || !currentUser) {
      return;
    }

    let cancelled = false;

    const syncRequests = async () => {
      try {
        const serverRequests = await fetchStudentRequests();
        if (cancelled) {
          return;
        }

        const nextRequests = serverRequests.map(request => ({
          id: `${request.salesDate}-${request.pluCode}`,
          pluCode: request.pluCode,
          productName: request.productName,
          qty: request.quantity,
          createdAt: new Date(request.requestedAt).toLocaleString('ko-KR'),
          salesDate: request.salesDate,
        }));

        await AsyncStorage.setItem(STORAGE_KEYS.requests, JSON.stringify(nextRequests));
        if (!cancelled) {
          setRequests(nextRequests);
        }
      } catch {
        // 서버 동기화 실패 시에는 마지막 로컬 요청 목록을 유지
      }
    };

    syncRequests();

    return () => {
      cancelled = true;
    };
  }, [currentUser, isInitializing]);

  useEffect(() => {
    if (isInitializing || !currentUser) {
      return;
    }

    let cancelled = false;

    const syncSuggestions = async () => {
      try {
        const serverSuggestions = await fetchSuggestions();
        if (cancelled) {
          return;
        }

        await saveSuggestions(serverSuggestions);
        if (!cancelled) {
          syncSuggestionsState(serverSuggestions);
        }
      } catch {
        // 서버 동기화 실패 시에는 마지막 로컬 건의사항 목록을 유지
      }
    };

    syncSuggestions();

    return () => {
      cancelled = true;
    };
  }, [currentUser, isInitializing]);

  const addRequest = async (item: RequestItem): Promise<boolean> => {
    try {
      const nextRequests = [item, ...requests];
      await AsyncStorage.setItem(STORAGE_KEYS.requests, JSON.stringify(nextRequests));
      setRequests(nextRequests);
      return true;
    } catch {
      return false;
    }
  };

  const removeRequest = async (requestId: string): Promise<boolean> => {
    try {
      const targetRequest = requests.find(request => request.id === requestId);
      if (!targetRequest) {
        return true;
      }

      await deleteStudentRequest({
        salesDate: targetRequest.salesDate,
        pluCode: targetRequest.pluCode,
      });

      const nextRequests = requests.filter(request => request.id !== requestId);
      await AsyncStorage.setItem(STORAGE_KEYS.requests, JSON.stringify(nextRequests));
      setRequests(nextRequests);
      return true;
    } catch {
      return false;
    }
  };

  const updateRequestQty = async (requestId: string, qty: number): Promise<boolean> => {
    try {
      const targetRequest = requests.find(request => request.id === requestId);
      if (!targetRequest) {
        return false;
      }

      const response = await submitStudentRequest({
        salesDate: targetRequest.salesDate,
        items: [
          {
            pluCode: targetRequest.pluCode,
            quantity: qty,
          },
        ],
      });

      const nextRequests = requests.map(request =>
        request.id === requestId ? {...request, qty, salesDate: response.salesDate} : request,
      );
      await AsyncStorage.setItem(STORAGE_KEYS.requests, JSON.stringify(nextRequests));
      setRequests(nextRequests);
      return true;
    } catch {
      return false;
    }
  };

  const loginGoogleUser = async (idToken: string): Promise<boolean> => {
    try {
      const auth = await loginGoogle({idToken});
      const loginId = auth.user.loginId || auth.user.email || auth.user.name;
      await AsyncStorage.multiSet([
        [STORAGE_KEYS.user, loginId],
        [STORAGE_KEYS.authToken, auth.accessToken],
      ]);
      setApiAuthToken(auth.accessToken);
      setCurrentUser(loginId);
      return true;
    } catch {
      return false;
    }
  };

  const addSuggestion = async (suggestion: Suggestion): Promise<boolean> => {
    try {
      const savedSuggestion = await createSuggestion({
        title: suggestion.title,
        content: suggestion.content,
      });
      const nextSuggestions = [savedSuggestion, ...suggestionsRef.current];
      await saveSuggestions(nextSuggestions);
      syncSuggestionsState(nextSuggestions);
      return true;
    } catch {
      return false;
    }
  };

  const updateSuggestion = async (
    nextSuggestion: Suggestion,
  ): Promise<boolean> => {
    try {
      const currentSuggestions = suggestionsRef.current;
      const targetSuggestion = currentSuggestions.find(item => item.id === nextSuggestion.id);
      if (!targetSuggestion) {
        return false;
      }

      const savedSuggestion = await updateSuggestionOnServer({
        id: targetSuggestion.id,
        title: nextSuggestion.title,
        content: nextSuggestion.content,
      });
      const nextSuggestions = currentSuggestions.map(item => (item.id === savedSuggestion.id ? savedSuggestion : item));
      await saveSuggestions(nextSuggestions);
      syncSuggestionsState(nextSuggestions);
      return true;
    } catch {
      return false;
    }
  };

  const removeSuggestion = async (suggestionId: string): Promise<boolean> => {
    try {
      const currentSuggestions = suggestionsRef.current;
      const targetSuggestion = currentSuggestions.find(item => item.id === suggestionId);
      if (!targetSuggestion) {
        return false;
      }

      await deleteSuggestionFromServer({
        id: targetSuggestion.id,
      });

      const nextSuggestions = currentSuggestions.filter(item => item.id !== suggestionId);
      await saveSuggestions(nextSuggestions);
      syncSuggestionsState(nextSuggestions);
      return true;
    } catch {
      return false;
    }
  };

  const removeSuggestionsBulk = async (
    suggestionIds: string[],
  ): Promise<{removedCount: number; failedCount: number}> => {
    try {
      let removedCount = 0;
      let failedCount = 0;

      const currentSuggestions = [...suggestionsRef.current];
      const selectableIds = new Set(currentSuggestions.map(item => item.id));
      const targetIds = suggestionIds.filter(id => selectableIds.has(id));

      if (targetIds.length === 0) {
        return {removedCount: 0, failedCount: suggestionIds.length};
      }

      const response = await deleteSuggestionsBulkFromServer({
        ids: targetIds,
      });
      removedCount = response.removedCount;
      failedCount = suggestionIds.length - removedCount;

      const nextSuggestions = await fetchSuggestions();
      await saveSuggestions(nextSuggestions);
      syncSuggestionsState(nextSuggestions);
      return {removedCount, failedCount};
    } catch {
      return {removedCount: 0, failedCount: suggestionIds.length};
    }
  };

  const logoutUser = async (): Promise<boolean> => {
    try {
      await AsyncStorage.multiRemove([STORAGE_KEYS.user, STORAGE_KEYS.authToken]);
      setApiAuthToken(null);
      setCurrentUser('');
      return true;
    } catch {
      return false;
    }
  };

  if (isInitializing) {
    return null;
  }

  return (
    <NavigationContainer>
      <Stack.Navigator
        initialRouteName={currentUser ? 'ProductList' : 'Login'}
        screenOptions={{headerShown: true}}>
        <Stack.Screen name="Login" options={{headerShown: false}}>
          {props => <LoginScreen {...props} loginGoogleUser={loginGoogleUser} />}
        </Stack.Screen>
        <Stack.Screen name="ProductList" options={{headerShown: false, title: '상품 목록'}}>
          {props => <ProductListScreen {...props} currentUser={currentUser} logoutUser={logoutUser} />}
        </Stack.Screen>
        <Stack.Screen name="ProductDetail" component={ProductDetailScreen} options={{title: '상품 상세'}} />
        <Stack.Screen name="RequestQty" options={{title: '수량 요청'}}>
          {props => <RequestQtyScreen {...props} addRequest={addRequest} />}
        </Stack.Screen>
        <Stack.Screen name="RequestDone" component={RequestDoneScreen} options={{title: '요청 완료'}} />
        <Stack.Screen name="MyRequests" options={{title: '내 요청 목록', headerBackTitle: '상품 목록'}}>
          {props => (
            <MyRequestsScreen
              {...props}
              requests={requests}
              removeRequest={removeRequest}
              updateRequestQty={updateRequestQty}
              currentUser={currentUser}
              logoutUser={logoutUser}
            />
          )}
        </Stack.Screen>
        <Stack.Screen name="Suggestions" options={{title: '건의사항', headerBackTitle: '상품 목록'}}>
          {props => (
            <SuggestionsScreen
              {...props}
              suggestions={suggestions}
              removeSuggestion={removeSuggestion}
              removeSuggestionsBulk={removeSuggestionsBulk}
            />
          )}
        </Stack.Screen>
        <Stack.Screen name="SuggestionWrite" options={{title: '건의사항 작성'}}>
          {props => (
            <SuggestionWriteScreen
              {...props}
              currentUser={currentUser}
              addSuggestion={addSuggestion}
            />
          )}
        </Stack.Screen>
        <Stack.Screen name="SuggestionEdit" options={{title: '건의사항'}}>
          {props => (
            <SuggestionEditScreen
              {...props}
              updateSuggestion={updateSuggestion}
            />
          )}
        </Stack.Screen>
        <Stack.Screen name="SuggestionDetail" options={{title: '건의사항'}}>
          {props => (
            <SuggestionDetailScreen
              {...props}
              removeSuggestion={removeSuggestion}
            />
          )}
        </Stack.Screen>
      </Stack.Navigator>
    </NavigationContainer>
  );
}



