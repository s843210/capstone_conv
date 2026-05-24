import React, {useEffect, useState} from 'react';
import {
  SafeAreaView,
  Text,
  Pressable,
  Alert,
  View,
  KeyboardAvoidingView,
  Platform,
  Image,
} from 'react-native';
import {GoogleSignin, statusCodes} from '@react-native-google-signin/google-signin';
import {LoginScreenProps} from '../types';
import {styles} from '../styles/commonStyles';
import {GOOGLE_SIGN_IN_SCOPES, GOOGLE_WEB_CLIENT_ID, hasGoogleClientId} from '../config/googleAuth';

type Props = LoginScreenProps & {
  loginGoogleUser: (idToken: string) => Promise<boolean>;
};

export default function LoginScreen({navigation, loginGoogleUser}: Props) {
  const [isGoogleSubmitting, setIsGoogleSubmitting] = useState(false);

  useEffect(() => {
    if (!hasGoogleClientId) {
      return;
    }

    GoogleSignin.configure({
      webClientId: GOOGLE_WEB_CLIENT_ID,
      scopes: GOOGLE_SIGN_IN_SCOPES,
      offlineAccess: false,
    });
  }, []);

  const startGoogleLogin = async () => {
    if (!hasGoogleClientId) {
      Alert.alert('설정 필요', 'Google Client ID가 설정되어 있지 않습니다.');
      return;
    }
    if (isGoogleSubmitting) {
      return;
    }

    setIsGoogleSubmitting(true);
    try {
      if (Platform.OS === 'android') {
        await GoogleSignin.hasPlayServices({showPlayServicesUpdateDialog: true});
      }

      const response = await GoogleSignin.signIn();
      if (response.type === 'cancelled') {
        return;
      }

      const idToken = response.data.idToken;
      if (!idToken) {
        Alert.alert('Google 로그인 오류', 'Google 인증 토큰을 받지 못했습니다.');
        return;
      }

      const saved = await loginGoogleUser(idToken);
      if (!saved) {
        Alert.alert('로그인 오류', 'Google 로그인 정보를 저장하지 못했습니다. 다시 시도해 주세요.');
        return;
      }

      navigation.replace('ProductList');
    } catch (error) {
      const errorCode =
        typeof error === 'object' && error !== null && 'code' in error
          ? String((error as {code?: unknown}).code)
          : '';
      if (errorCode === statusCodes.SIGN_IN_CANCELLED) {
        return;
      }

      Alert.alert('Google 로그인 오류', 'Google 로그인에 실패했습니다. 다시 시도해 주세요.');
    } finally {
      setIsGoogleSubmitting(false);
    }
  };

  return (
    <SafeAreaView style={styles.loginPage}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.loginKeyboardWrap}>
        <View style={styles.loginContent}>
          <View style={styles.loginHeader}>
            <Text style={styles.loginAppTitle}>CoopsPick</Text>
            <Text style={styles.loginIntroText}>
              조선대학교 IT융합대학 5층 Coopsket 전용 앱입니다.
            </Text>
            <Text style={styles.loginDescription}>
              쿱스켓의 상품과 재고를 확인하고, 필요한 상품을 간편하게 요청해보세요.
            </Text>
          </View>

          <View style={styles.loginLogoWrap}>
            <Image
              source={require('../../assets/images/chosunlogo.png')}
              style={styles.loginLogo}
              resizeMode="contain"
            />
          </View>

          <View style={styles.loginCard}>
            <Pressable
              style={[
                styles.loginGoogleBtn,
                (!hasGoogleClientId || isGoogleSubmitting) && styles.loginGoogleBtnDisabled,
              ]}
              onPress={startGoogleLogin}
              disabled={!hasGoogleClientId || isGoogleSubmitting}>
              <Text style={styles.loginGoogleBtnText}>
                {isGoogleSubmitting ? 'Google 로그인 중...' : 'Google로 로그인'}
              </Text>
            </Pressable>
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
